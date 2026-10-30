"""LiveKit worker: `python -m studio_runtime.worker start` (`download-files` once for the VAD).

One worker serves every agent: the dispatch metadata names the agent, and its settings come from
the API when the call starts. LiveKit serves the health check at `/` on `health_port`.
"""

import logging

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AgentStateChangedEvent,
    JobContext,
    JobExecutorType,
    JobProcess,
    cli,
    room_io,
    vad,
)
from livekit.plugins import silero
from livekit.plugins.langchain import LLMAdapter

from studio_runtime.channels import parse_call_metadata, register_voice_toggle, set_voice
from studio_runtime.config import Settings, get_settings
from studio_runtime.control_plane import AgentConfig, CallRecord, create_control_plane_client
from studio_runtime.conversation import build_transcript, create_llm
from studio_runtime.flows.call import create_flow_llm, create_flow_runner
from studio_runtime.flows.runner import FlowRunner
from studio_runtime.knowledge import build_knowledge_tool
from studio_runtime.languages import FALLBACK_LANGUAGE, build_instructions, load_locale
from studio_runtime.observability import (
    CallTracing,
    LlmCallTracer,
    TurnLatencies,
    create_tracer_provider,
)
from studio_runtime.providers import build_turn_handling, create_stt, create_tts

logger = logging.getLogger(__name__)

VAD_USERDATA_KEY = "vad"
TRACER_PROVIDER_USERDATA_KEY = "tracer_provider"
TRANSCRIPTION_TOPIC = "lk.transcription"
LISTENING_STATE = "listening"


def prewarm_process(process: JobProcess) -> None:
    process.userdata[VAD_USERDATA_KEY] = silero.VAD.load()
    process.userdata[TRACER_PROVIDER_USERDATA_KEY] = create_tracer_provider(get_settings())


def build_agent_session(
    config: AgentConfig, language: str, vad_model: vad.VAD, llm: LLMAdapter, settings: Settings
) -> AgentSession:
    voice = config.language_settings[language]
    return AgentSession(
        vad=vad_model,
        stt=create_stt(voice, language, settings),
        llm=llm,
        tts=create_tts(voice, language),
        turn_handling=build_turn_handling(settings),
    )


def end_after_final_message(session: AgentSession, runner: FlowRunner) -> None:
    """When the flow reaches an End or Transfer node, hang up once its message has been said."""

    def on_state_changed(event: AgentStateChangedEvent) -> None:
        if runner.ended and event.new_state == LISTENING_STATE:
            session.shutdown()

    session.on("agent_state_changed", on_state_changed)


async def run_call(ctx: JobContext) -> None:
    settings = get_settings()
    metadata = parse_call_metadata(ctx.job.metadata)
    control_plane = create_control_plane_client(settings)
    tracer_provider = ctx.proc.userdata[TRACER_PROVIDER_USERDATA_KEY]
    if tracer_provider is not None:
        ctx.add_shutdown_callback(CallTracing(tracer_provider, session_id=ctx.room.name).flush)
    callbacks = [LlmCallTracer()]
    await ctx.connect()
    try:
        config = await control_plane.get_agent_config(metadata.agent_id, metadata.flow)
    except Exception:
        logger.exception("could not load agent %s", metadata.agent_id)
        if metadata.is_web:
            message = load_locale(FALLBACK_LANGUAGE).messages["agent_unavailable"]
            await ctx.room.local_participant.send_text(message, topic=TRANSCRIPTION_TOPIC)
        await control_plane.aclose()
        ctx.shutdown()
        return

    language = config.starting_language
    locale = load_locale(language)
    knowledge_tool = (
        build_knowledge_tool(control_plane, config.id, locale)
        if config.knowledge_base_ids
        else None
    )
    runner = None
    if config.flow is not None:
        runner = create_flow_runner(
            config, language, settings, ctx.room, knowledge_tool, locale.messages["knowledge_rule"]
        )
        await runner.start()
        instructions = build_instructions(config.instructions, locale, has_knowledge=False)
        llm = create_flow_llm(runner, config, instructions, settings, callbacks)
    else:
        has_knowledge = knowledge_tool is not None
        instructions = build_instructions(config.instructions, locale, has_knowledge)
        tools = [knowledge_tool] if has_knowledge else []
        llm = create_llm(config.llm_model, tools, settings, callbacks)

    call_id = await control_plane.start_call(config.id, ctx.room.name, metadata.channel)
    session = build_agent_session(
        config, language, ctx.proc.userdata[VAD_USERDATA_KEY], llm, settings
    )
    latencies = TurnLatencies()
    session.on("conversation_item_added", latencies.on_conversation_item_added)

    async def close_call_record() -> None:
        record = CallRecord(
            transcript=build_transcript(session.history), turn_latency_ms=latencies.turns
        )
        if runner is not None:
            record.outcome, record.fields, record.flow_path = (
                runner.outcome,
                runner.fields,
                runner.path,
            )
        try:
            await control_plane.end_call(call_id, record)
        finally:
            await control_plane.aclose()
            if runner is not None:
                await runner.aclose()

    ctx.add_shutdown_callback(close_call_record)
    if runner is not None:
        end_after_final_message(session, runner)
    # The tester or caller leaving closes the session; deleting the room then ends the job.
    await session.start(
        agent=Agent(instructions=instructions),
        room=ctx.room,
        room_options=room_io.RoomOptions(delete_room_on_close=True),
    )
    if metadata.is_web:
        set_voice(session, enabled=False)
        register_voice_toggle(ctx.room, session, config.greeting)
    session.say(config.greeting)


def create_server(settings: Settings) -> AgentServer:
    # One process per call: the tracer provider that points spans at Langfuse is process-wide.
    server = AgentServer(
        setup_fnc=prewarm_process,
        job_executor_type=JobExecutorType.PROCESS,
        num_idle_processes=settings.num_idle_processes,
        port=settings.health_port,
        load_threshold=settings.worker_load_threshold,
    )
    server.rtc_session(agent_name=settings.agent_name)(run_call)
    return server


if __name__ == "__main__":
    cli.run_app(create_server(get_settings()))

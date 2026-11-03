"""LiveKit worker: `python -m studio_runtime.worker start` (`download-files` once for the VAD).

One worker serves every agent: the dispatch metadata names the agent, and its settings come from
the API when the call starts. LiveKit serves the health check at `/` on `health_port`.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AgentStateChangedEvent,
    ConversationItemAddedEvent,
    JobContext,
    JobExecutorType,
    JobProcess,
    cli,
    room_io,
    vad,
)
from livekit.plugins import silero
from livekit.plugins.langchain import LLMAdapter

from studio_runtime.channels import (
    CallMetadata,
    parse_call_metadata,
    register_idle_caller,
    register_voice_toggle,
    set_voice,
)
from studio_runtime.config import Settings, get_settings
from studio_runtime.control_plane import (
    INBOUND_DIRECTION,
    OUTBOUND_DIRECTION,
    AgentConfig,
    CallRecord,
    ControlPlaneClient,
    create_control_plane_client,
)
from studio_runtime.conversation import build_transcript, create_llm
from studio_runtime.flows.call import create_flow_llm, create_flow_runner
from studio_runtime.flows.http_tools import fill_leniently
from studio_runtime.flows.runner import FlowRunner
from studio_runtime.knowledge import build_knowledge_tool
from studio_runtime.languages import FALLBACK_LANGUAGE, build_instructions, load_locale
from studio_runtime.observability import (
    CallTracing,
    LlmCallTracer,
    TurnLatencies,
    call_usage,
    create_tracer_provider,
)
from studio_runtime.phone import (
    CALLEE_IDENTITY,
    TRANSFER_FAILED_OUTCOME,
    TRANSFERRED_OUTCOME,
    PhoneLine,
    answer,
    caller_line,
    ring,
    transfer,
)
from studio_runtime.providers import build_turn_handling, create_stt, create_tts

logger = logging.getLogger(__name__)

# Flows can use the number on the other end in tools, like a field ("" on browser calls).
CALLER_NUMBER_VALUE = "caller_number"
KNOWN_DETAILS_HEADING = "About the person on this call: "

VAD_USERDATA_KEY = "vad"
TRACER_PROVIDER_USERDATA_KEY = "tracer_provider"
TRANSCRIPTION_TOPIC = "lk.transcription"
LISTENING_STATE = "listening"
ASSISTANT_ROLE = "assistant"


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
        user_away_timeout=settings.caller_away_seconds,
    )


def end_after_final_message(
    session: AgentSession, runner: FlowRunner, on_heard: Callable[[], None] | None = None
) -> None:
    """When the flow reaches an End or Transfer node, hang up (or run `on_heard`, once) when
    its message has been heard in full. A message the caller talked over is said again on the
    next turn (FlowGraph), so a booking's ID is never lost to an interruption."""
    done = False

    def finish() -> None:
        nonlocal done
        if done:
            return
        done = True
        (on_heard or session.shutdown)()

    def on_item_added(event: ConversationItemAddedEvent) -> None:
        message = event.item
        if (
            runner.ended
            and runner.final_message
            and getattr(message, "role", None) == ASSISTANT_ROLE
            and runner.final_message in message.text_content
            and not message.interrupted
        ):
            finish()

    def on_state_changed(event: AgentStateChangedEvent) -> None:
        # Ended with nothing to say (a tool node with no way on): hang up once quiet.
        if runner.ended and not runner.final_message and event.new_state == LISTENING_STATE:
            finish()

    session.on("conversation_item_added", on_item_added)
    session.on("agent_state_changed", on_state_changed)


async def hand_over_or_hang_up(
    ctx: JobContext, session: AgentSession, runner: FlowRunner, line: PhoneLine, sorry: str
) -> None:
    """After a Transfer node's message on a phone call, hands the caller to its destination;
    if that fails, says so before hanging up. Other calls just end."""
    if runner.transfer_to and line.identity:
        moved = await transfer(ctx.api, ctx.room.name, line.identity, runner.transfer_to)
        line.outcome = TRANSFERRED_OUTCOME if moved else TRANSFER_FAILED_OUTCOME
        if not moved:
            await session.say(sorry)
    session.shutdown()


def in_background(work: Callable[[], Coroutine[Any, Any, None]]) -> Callable[[], None]:
    """An event handler that starts `work` as a task (kept referenced until it finishes)."""
    pending: set[asyncio.Task] = set()

    def start() -> None:
        task = asyncio.get_running_loop().create_task(work())
        pending.add(task)
        task.add_done_callback(pending.discard)

    return start


def personalise(config: AgentConfig, variables: dict[str, str]) -> None:
    """A campaign contact's details fill {name}-style placeholders in the greeting and the
    voicemail message, and are told to the LLM. A placeholder with no value is left out, so
    a test call never says "{name}" aloud."""
    config.greeting = fill_leniently(config.greeting, variables)
    config.voicemail_message = fill_leniently(config.voicemail_message, variables)
    known = "; ".join(f"{name}: {value}" for name, value in variables.items() if value)
    if known:
        config.instructions = f"{config.instructions}\n\n{KNOWN_DETAILS_HEADING}{known}."


async def agent_for(control_plane: ControlPlaneClient, metadata: CallMetadata) -> str:
    """The agent named in the dispatch, or the one the dialled number is bound to now."""
    if metadata.agent_id is not None:
        return metadata.agent_id
    number = await control_plane.get_phone_number(metadata.number_id)
    if number.agent_id is None:
        raise LookupError(f"{number.number} is not bound to an agent")
    return number.agent_id


async def ring_and_answer(
    ctx: JobContext,
    session: AgentSession,
    metadata: CallMetadata,
    config: AgentConfig,
    line: PhoneLine,
    settings: Settings,
) -> None:
    try:
        category = await ring(
            ctx.api,
            ctx.room.name,
            metadata.dial_to,
            metadata.outbound_trunk_id,
            settings.amd_llm_model,
            session,
        )
    except Exception:
        logger.exception("could not ring %s", metadata.dial_to)
        category = None
    if category is not None:
        line.identity = CALLEE_IDENTITY
    line.outcome = answer(session, category, config.greeting, config.voicemail_message)


async def run_call(ctx: JobContext) -> None:
    settings = get_settings()
    metadata = parse_call_metadata(ctx.job.metadata)
    control_plane = create_control_plane_client(settings)
    tracer_provider = ctx.proc.userdata[TRACER_PROVIDER_USERDATA_KEY]
    if tracer_provider is not None:
        ctx.add_shutdown_callback(CallTracing(tracer_provider, session_id=ctx.room.name).flush)
    llm_tracer = LlmCallTracer()
    callbacks = [llm_tracer]
    await ctx.connect()
    # An incoming caller is already in the room; an outgoing call is rung once the session runs.
    line = PhoneLine(remote_number=metadata.dial_to)
    if not metadata.is_web and not metadata.is_outbound:
        line = caller_line(await ctx.wait_for_participant())
    try:
        config = await control_plane.get_agent_config(
            await agent_for(control_plane, metadata), metadata.flow
        )
    except Exception:
        logger.exception("could not load the agent for %s", ctx.job.metadata)
        if metadata.is_web:
            message = load_locale(FALLBACK_LANGUAGE).messages["agent_unavailable"]
            await ctx.room.local_participant.send_text(message, topic=TRANSCRIPTION_TOPIC)
        await control_plane.aclose()
        ctx.shutdown()
        return

    personalise(config, metadata.variables)
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
            config,
            language,
            settings,
            ctx.room,
            knowledge_tool,
            locale.messages,
            {CALLER_NUMBER_VALUE: line.remote_number or "", **metadata.variables},
        )
        await runner.start()
        instructions = build_instructions(config.instructions, locale, has_knowledge=False)
        llm = create_flow_llm(runner, config, instructions, settings, callbacks)
    else:
        has_knowledge = knowledge_tool is not None
        instructions = build_instructions(config.instructions, locale, has_knowledge)
        tools = [knowledge_tool] if has_knowledge else []
        llm = create_llm(config.llm_model, tools, settings, callbacks)

    direction = OUTBOUND_DIRECTION if metadata.is_outbound else INBOUND_DIRECTION
    call_id = await control_plane.start_call(
        config.id,
        ctx.room.name,
        metadata.channel,
        direction,
        line.remote_number,
        metadata.campaign_contact_id,
        # The call's page links to LiveKit's recording of this room session.
        await ctx.room.sid,
    )
    session = build_agent_session(
        config, language, ctx.proc.userdata[VAD_USERDATA_KEY], llm, settings
    )
    latencies = TurnLatencies()
    session.on("conversation_item_added", latencies.on_conversation_item_added)

    async def close_call_record() -> None:
        record = CallRecord(
            transcript=build_transcript(session.history),
            turn_latency_ms=latencies.turns,
            interruptions=latencies.interruptions,
            usage=call_usage(session.usage.model_usage, llm_tracer),
        )
        if runner is not None:
            record.outcome, record.fields, record.flow_path, record.tool_calls = (
                runner.outcome,
                runner.fields,
                runner.path,
                runner.tool_calls,
            )
        # Ended on the phone side: nobody answered, voicemail, or the transfer.
        record.outcome = line.outcome or record.outcome
        try:
            await control_plane.end_call(call_id, record)
        finally:
            await control_plane.aclose()
            if runner is not None:
                await runner.aclose()

    ctx.add_shutdown_callback(close_call_record)
    if runner is not None:
        sorry = locale.messages["transfer_failed"]
        end_after_final_message(
            session,
            runner,
            in_background(lambda: hand_over_or_hang_up(ctx, session, runner, line, sorry)),
        )
    # The tester or caller leaving closes the session; deleting the room then ends the job.
    # An outgoing call's session waits for the person rung, not whoever joins first.
    callee = {"participant_identity": CALLEE_IDENTITY} if metadata.is_outbound else {}
    await session.start(
        agent=Agent(instructions=instructions),
        room=ctx.room,
        room_options=room_io.RoomOptions(delete_room_on_close=True, **callee),
    )
    register_idle_caller(session, locale.messages["still_there"], locale.messages["goodbye_quiet"])
    if metadata.is_outbound:
        await ring_and_answer(ctx, session, metadata, config, line, settings)
        return
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

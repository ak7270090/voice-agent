"""LiveKit worker: `python -m studio_runtime.worker start` (`download-files` once for the VAD).

One worker serves every agent: the dispatch metadata names the agent, and its settings come from
the API when the call starts. LiveKit serves the health check at `/` on `health_port`.
"""

import logging

from langchain_core.tools import BaseTool
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
    vad,
)
from livekit.plugins import silero

from studio_runtime.channels import parse_call_metadata, register_voice_toggle, set_voice
from studio_runtime.config import Settings, get_settings
from studio_runtime.control_plane import AgentConfig, create_control_plane_client
from studio_runtime.conversation import build_transcript, create_llm
from studio_runtime.knowledge import build_knowledge_tool
from studio_runtime.languages import FALLBACK_LANGUAGE, build_instructions, load_locale
from studio_runtime.providers import create_stt, create_tts

logger = logging.getLogger(__name__)

VAD_USERDATA_KEY = "vad"
TRANSCRIPTION_TOPIC = "lk.transcription"


def prewarm_process(process: JobProcess) -> None:
    process.userdata[VAD_USERDATA_KEY] = silero.VAD.load()


def build_agent_session(
    config: AgentConfig,
    language: str,
    vad_model: vad.VAD,
    tools: list[BaseTool],
    settings: Settings,
) -> AgentSession:
    voice = config.language_settings[language]
    return AgentSession(
        vad=vad_model,
        stt=create_stt(voice, language, settings),
        llm=create_llm(config.llm_model, tools, settings),
        tts=create_tts(voice),
    )


async def run_call(ctx: JobContext) -> None:
    settings = get_settings()
    metadata = parse_call_metadata(ctx.job.metadata)
    control_plane = create_control_plane_client(settings)
    await ctx.connect()
    try:
        config = await control_plane.get_agent_config(metadata.agent_id)
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
    has_knowledge = bool(config.knowledge_base_ids)
    tools = [build_knowledge_tool(control_plane, config.id, locale)] if has_knowledge else []
    call_id = await control_plane.start_call(config.id, ctx.room.name, metadata.channel)
    session = build_agent_session(
        config, language, ctx.proc.userdata[VAD_USERDATA_KEY], tools, settings
    )

    async def close_call_record() -> None:
        try:
            await control_plane.end_call(call_id, build_transcript(session.history))
        finally:
            await control_plane.aclose()

    ctx.add_shutdown_callback(close_call_record)
    instructions = build_instructions(config.instructions, locale, has_knowledge)
    # The tester or caller leaving closes the session; deleting the room then ends the job.
    await session.start(
        agent=Agent(instructions=instructions),
        room=ctx.room,
        room_options=room_io.RoomOptions(delete_room_on_close=True),
    )
    if metadata.is_web:
        set_voice(session, enabled=False)
        register_voice_toggle(ctx.room, session)
    session.say(config.greeting)


def create_server(settings: Settings) -> AgentServer:
    server = AgentServer(
        setup_fnc=prewarm_process,
        port=settings.health_port,
        load_threshold=settings.worker_load_threshold,
    )
    server.rtc_session(agent_name=settings.agent_name)(run_call)
    return server


if __name__ == "__main__":
    cli.run_app(create_server(get_settings()))

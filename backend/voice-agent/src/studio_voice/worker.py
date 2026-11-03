"""LiveKit worker: `python -m studio_voice.worker start` (`download-files` once for the VAD).

One worker serves every agent: the dispatch metadata names the agent, and its settings come from
the backend when the call starts. LiveKit serves the health check at `/` on `health_port`.
"""

from livekit.agents import AgentServer, JobExecutorType, JobProcess, cli
from livekit.plugins import silero

from studio_voice.call.session import TRACER_PROVIDER_USERDATA_KEY, VAD_USERDATA_KEY, run_call
from studio_voice.core.config import Settings, get_settings
from studio_voice.core.observability import create_tracer_provider


def prewarm_process(process: JobProcess) -> None:
    process.userdata[VAD_USERDATA_KEY] = silero.VAD.load()
    process.userdata[TRACER_PROVIDER_USERDATA_KEY] = create_tracer_provider(get_settings())


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

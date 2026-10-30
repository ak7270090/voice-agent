"""LiveKit worker: `python -m studio_runtime.worker start` (or `dev` for auto-reload).

LiveKit serves the health check at `/` on `health_port`. Until Phase 1 loads agents from the API,
the worker only joins the rooms it is dispatched to.
"""

import logging

from livekit.agents import AgentServer, JobContext, cli

from studio_runtime.config import Settings, get_settings

logger = logging.getLogger(__name__)


async def run_call(ctx: JobContext) -> None:
    await ctx.connect()
    logger.info("joined room %s", ctx.room.name)


def create_server(settings: Settings) -> AgentServer:
    server = AgentServer(port=settings.health_port, load_threshold=settings.worker_load_threshold)
    server.rtc_session(agent_name=settings.agent_name)(run_call)
    return server


if __name__ == "__main__":
    cli.run_app(create_server(get_settings()))

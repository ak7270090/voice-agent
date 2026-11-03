"""The API's part of a call's trace.

The runtime sends a W3C `traceparent` header with each request it makes during a call (agent
config, knowledge search, the flow's HTTP tools, the call record). FastAPI's instrumentation
continues that trace, so those requests appear in Langfuse inside the turn that made them.
Requests that arrive without one (the console, health checks) start no trace: the sampler only
follows a parent's decision.
"""

import logging

import httpx
from fastapi import FastAPI
from langfuse import Langfuse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ParentBased

from studio_api.config import Settings

logger = logging.getLogger(__name__)

# Lists the projects the API keys belong to (one, for project keys).
LANGFUSE_PROJECTS_PATH = "/api/public/projects"


def create_tracer_provider(settings: Settings) -> TracerProvider | None:
    """None when the Langfuse keys are not set."""
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        logger.info("Langfuse keys not set; the API is not traced")
        return None
    tracer_provider = follow_callers_tracer_provider()
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
        tracer_provider=tracer_provider,
        should_export_span=lambda span: True,
    )
    return tracer_provider


def follow_callers_tracer_provider() -> TracerProvider:
    """Records a request only when its caller's trace is being recorded (a `traceparent` with
    the sampled flag); a request that would start a new trace is not recorded."""
    return TracerProvider(sampler=ParentBased(root=ALWAYS_OFF))


async def find_langfuse_project(settings: Settings, http: httpx.AsyncClient) -> str | None:
    """The project the keys belong to, for links from a call to its Langfuse session. None
    when tracing is off or Langfuse cannot be reached (calls then have no link)."""
    if settings.langfuse_project_id:
        return settings.langfuse_project_id
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    try:
        response = await http.get(
            f"{settings.langfuse_base_url.rstrip('/')}{LANGFUSE_PROJECTS_PATH}",
            auth=(settings.langfuse_public_key, settings.langfuse_secret_key),
        )
        response.raise_for_status()
        projects = response.json()["data"]
    except (httpx.HTTPError, KeyError, ValueError):
        logger.warning("could not look up the Langfuse project; calls get no trace link")
        return None
    return projects[0]["id"] if projects else None


def trace_requests(app: FastAPI, tracer_provider: TracerProvider | None) -> None:
    if tracer_provider is not None:
        # One span per request; the ASGI send/receive sub-spans add nothing to a call's trace.
        FastAPIInstrumentor.instrument_app(
            app, tracer_provider=tracer_provider, exclude_spans=["send", "receive"]
        )

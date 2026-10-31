"""The API's part of a call's trace.

The runtime sends a W3C `traceparent` header with each request it makes during a call (agent
config, knowledge search, the flow's HTTP tools, the call record). FastAPI's instrumentation
continues that trace, so those requests appear in Langfuse inside the turn that made them.
Requests that arrive without one (the console, health checks) start no trace: the sampler only
follows a parent's decision.
"""

import logging

from fastapi import FastAPI
from langfuse import Langfuse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ParentBased

from studio_api.config import Settings

logger = logging.getLogger(__name__)


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


def trace_requests(app: FastAPI, tracer_provider: TracerProvider | None) -> None:
    if tracer_provider is not None:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

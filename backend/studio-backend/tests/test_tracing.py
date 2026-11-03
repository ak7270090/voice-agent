import httpx
from fastapi import FastAPI
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from studio_backend.config import Settings
from studio_backend.tracing import (
    create_tracer_provider,
    follow_callers_tracer_provider,
    trace_requests,
)

RUNTIME_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
TRACEPARENT = f"00-{RUNTIME_TRACE_ID}-00f067aa0ba902b7-01"


def test_the_api_is_not_traced_without_langfuse_keys():
    assert create_tracer_provider(Settings(langfuse_public_key="", langfuse_secret_key="")) is None


async def test_only_requests_inside_a_callers_trace_are_recorded():
    exporter = InMemorySpanExporter()
    tracer_provider = follow_callers_tracer_provider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    app = FastAPI()
    app.get("/demo-clinic/availability")(lambda: {"free_times": []})
    trace_requests(app, tracer_provider)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/demo-clinic/availability")
        await client.get("/demo-clinic/availability", headers={"traceparent": TRACEPARENT})

    trace_ids = {format(span.context.trace_id, "032x") for span in exporter.get_finished_spans()}
    assert trace_ids == {RUNTIME_TRACE_ID}

"""Tracing to Langfuse over OpenTelemetry, and how long each turn took.

Follows LiveKit's documented pattern: LiveKit's own `set_tracer_provider` (its session, LLM and
voice spans read from it), one Langfuse session per call, every span exported. Adapted from
clinic-voice-agent, where it priced each LLM call and measured voice-to-voice latency.
"""

import asyncio
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from langfuse import Langfuse
from livekit.agents import ConversationItemAddedEvent
from livekit.agents.llm import ChatMessage
from livekit.agents.telemetry import set_tracer_provider, tracer
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Span

from studio_runtime.config import Settings

logger = logging.getLogger(__name__)

LANGFUSE_SESSION_ID_ATTRIBUTE = "langfuse.session.id"
LANGFUSE_OBSERVATION_TYPE = "langfuse.observation.type"
LANGFUSE_OBSERVATION_INPUT = "langfuse.observation.input"
LANGFUSE_OBSERVATION_OUTPUT = "langfuse.observation.output"
LANGFUSE_USAGE_DETAILS = "langfuse.observation.usage_details"
GEN_AI_MODEL = "gen_ai.request.model"
LLM_CALL_SPAN_NAME = "llm_call"
TOOL_OBSERVATION = "tool"
# Passed by FlowGraph in each LLM call's LangChain metadata; shown on the llm_call span.
FLOW_STEP_KEY = "flow.step"

# Seconds, from LiveKit's per-message metrics. e2e_latency is voice-to-voice: from the caller
# stopping to the agent's first audio.
LATENCY_FIELDS = (
    "end_of_turn_delay",
    "transcription_delay",
    "llm_node_ttft",
    "tts_node_ttfb",
    "e2e_latency",
)


def create_tracer_provider(settings: Settings) -> TracerProvider | None:
    """Built once per process at prewarm (the Langfuse client takes ~100 ms to create).
    None when the Langfuse keys are not set."""
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        logger.info("Langfuse keys not set; tracing is off")
        return None
    tracer_provider = TracerProvider()
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
        tracer_provider=tracer_provider,
        should_export_span=lambda span: True,
    )
    return tracer_provider


class CallTracing:
    """Points LiveKit's spans for one call at Langfuse, grouped as one Langfuse session.

    The tracer provider is process-wide, so each call runs in its own process.
    """

    def __init__(self, tracer_provider: TracerProvider, session_id: str) -> None:
        self.tracer_provider = tracer_provider
        set_tracer_provider(tracer_provider, metadata={LANGFUSE_SESSION_ID_ATTRIBUTE: session_id})

    async def flush(self) -> None:
        # The exporter sends spans over blocking HTTP; keep it off the call's event loop.
        await asyncio.to_thread(self.tracer_provider.force_flush)


class LlmCallTracer(BaseCallbackHandler):
    """One Langfuse generation per LLM call, with model and token usage, so Langfuse prices it,
    and one tool observation per tool call, with its arguments, result and duration.

    LiveKit's LangChain adapter reports no usage, and the flow runs its tools itself, so LiveKit
    has no span for them; each gets one here.
    """

    run_inline = True

    def __init__(self) -> None:
        self._open_spans: dict[UUID, Span] = {}

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        span = tracer.start_span(LLM_CALL_SPAN_NAME)
        span.set_attribute(LANGFUSE_OBSERVATION_TYPE, "generation")
        prompt = [{"role": m.type, "content": m.text} for m in messages[0]] if messages else []
        span.set_attribute(LANGFUSE_OBSERVATION_INPUT, json.dumps(prompt, ensure_ascii=False))
        step = (metadata or {}).get(FLOW_STEP_KEY)
        if step:
            span.set_attribute(FLOW_STEP_KEY, step)
        self._open_spans[run_id] = span

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        span = self._open_spans.pop(run_id, None)
        if span is None:
            return
        for name, value in llm_call_attributes(response).items():
            span.set_attribute(name, value)
        span.end()

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._end_with_error(run_id, error)

    def on_tool_start(
        self,
        serialized: dict[str, Any] | None,
        input_str: str,
        *,
        run_id: UUID,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        span = tracer.start_span((serialized or {}).get("name") or TOOL_OBSERVATION)
        span.set_attribute(LANGFUSE_OBSERVATION_TYPE, TOOL_OBSERVATION)
        arguments = json.dumps(inputs, default=str) if inputs is not None else input_str
        span.set_attribute(LANGFUSE_OBSERVATION_INPUT, arguments)
        self._open_spans[run_id] = span

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        span = self._open_spans.pop(run_id, None)
        if span is not None:
            span.set_attribute(LANGFUSE_OBSERVATION_OUTPUT, str(getattr(output, "content", output)))
            span.end()

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._end_with_error(run_id, error)

    def _end_with_error(self, run_id: UUID, error: BaseException) -> None:
        span = self._open_spans.pop(run_id, None)
        if span is not None:
            span.record_exception(error)
            span.end()


@contextmanager
def flow_span(name: str, observation_input: Any = None) -> Iterator[Span]:
    """A span around the flow's own code (reading an answer, a move, saving fields), so the
    trace shows what the flow did between LLM calls. A no-op when tracing is off."""
    with tracer.start_as_current_span(name) as span:
        if observation_input is not None:
            span.set_attribute(
                LANGFUSE_OBSERVATION_INPUT, json.dumps(observation_input, default=str)
            )
        yield span


def set_span_output(span: Span, output: Any) -> None:
    span.set_attribute(LANGFUSE_OBSERVATION_OUTPUT, json.dumps(output, default=str))


def llm_call_attributes(response: LLMResult) -> dict[str, str | int]:
    """Model, usage (cached input is priced lower) and output of one LLM call, as attributes."""
    message = getattr(response.generations[0][0], "message", None) if response.generations else None
    if message is None:
        return {}
    attributes: dict[str, str | int] = {}
    model = message.response_metadata.get("model_name")
    if model:
        attributes[GEN_AI_MODEL] = model
    usage = getattr(message, "usage_metadata", None)
    if usage:
        cached = (usage.get("input_token_details") or {}).get("cache_read", 0)
        usage_details = {
            "input": usage["input_tokens"] - cached,
            "input_cached_tokens": cached,
            "output": usage["output_tokens"],
        }
        attributes[LANGFUSE_USAGE_DETAILS] = json.dumps(usage_details)
    tool_calls = [
        {"name": call["name"], "args": call.get("args", {})}
        for call in getattr(message, "tool_calls", [])
    ]
    output = {"text": message.text, "tool_calls": tool_calls}
    attributes[LANGFUSE_OBSERVATION_OUTPUT] = json.dumps(output, ensure_ascii=False)
    return attributes


class TurnLatencies:
    """Collects each turn's latency in milliseconds for the call record.

    LiveKit puts end-of-turn and transcription delays on the caller's message and the LLM, voice
    and voice-to-voice times on the agent's reply; one turn joins the two.
    """

    def __init__(self) -> None:
        self.turns: list[dict[str, float]] = []
        self._caller_part: dict[str, float] = {}

    def on_conversation_item_added(self, event: ConversationItemAddedEvent) -> None:
        message = event.item
        if not isinstance(message, ChatMessage) or message.role not in ("user", "assistant"):
            return
        latency_ms = {
            field: round(message.metrics[field] * 1000)
            for field in LATENCY_FIELDS
            if message.metrics.get(field) is not None
        }
        if message.role == "user":
            self._caller_part = latency_ms
            return
        if latency_ms:
            turn = {**self._caller_part, **latency_ms}
            self.turns.append(turn)
            logger.info("turn latency", extra=turn)
        self._caller_part = {}

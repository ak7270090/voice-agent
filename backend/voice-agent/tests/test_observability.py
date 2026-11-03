from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from livekit.agents.llm import ChatMessage
from livekit.agents.metrics import LLMModelUsage, STTModelUsage, TTSModelUsage
from livekit.agents.telemetry import tracer

from studio_voice.config import Settings
from studio_voice.observability import (
    LlmCallTracer,
    TurnLatencies,
    add_trace_context,
    call_usage,
    create_tracer_provider,
    llm_call_attributes,
)
from studio_voice.speech_providers import build_turn_handling


def test_tracing_is_off_without_langfuse_keys():
    assert create_tracer_provider(Settings(langfuse_public_key="", langfuse_secret_key="")) is None


def test_llm_call_is_priced_from_its_model_and_usage():
    message = AIMessage(
        content="",
        tool_calls=[{"name": "save_fields", "args": {"day": "Monday"}, "id": "c1"}],
        response_metadata={"model_name": "gpt-4.1-mini"},
        usage_metadata={
            "input_tokens": 900,
            "output_tokens": 20,
            "total_tokens": 920,
            "input_token_details": {"cache_read": 600},
        },
    )

    attributes = llm_call_attributes(LLMResult(generations=[[ChatGeneration(message=message)]]))

    assert attributes["gen_ai.request.model"] == "gpt-4.1-mini"
    assert attributes["langfuse.observation.usage_details"] == (
        '{"input": 300, "input_cached_tokens": 600, "output": 20}'
    )
    assert '"save_fields"' in attributes["langfuse.observation.output"]


def test_a_calls_usage_adds_langchain_tokens_to_livekits_speech_and_voice_counts():
    tracer_ = LlmCallTracer()
    for tokens in (900, 400):
        message = AIMessage(
            content="Hi",
            usage_metadata={
                "input_tokens": tokens,
                "output_tokens": 10,
                "total_tokens": tokens + 10,
                "input_token_details": {"cache_read": 100},
            },
        )
        tracer_.on_llm_end(
            LLMResult(generations=[[ChatGeneration(message=message)]]), run_id=uuid4()
        )
    model_usage = [
        STTModelUsage(provider="deepgram", model="nova-3", audio_duration=61.24),
        TTSModelUsage(provider="deepgram", model="aura-2", characters_count=420),
        LLMModelUsage(provider="livekit", model="gpt-4.1-mini", input_tokens=50, output_tokens=5),
    ]

    usage = call_usage(model_usage, tracer_)

    assert usage == {
        "llm_input_tokens": 1350,
        "llm_cached_input_tokens": 200,
        "llm_output_tokens": 25,
        "stt_seconds": 61.2,
        "tts_characters": 420,
    }


def test_agent_reply_latencies_are_kept_in_milliseconds():
    latencies = TurnLatencies()
    caller = ChatMessage(role="user", content=["Hello"])
    caller.metrics = {"end_of_turn_delay": 0.4, "transcription_delay": 0.2}
    reply = ChatMessage(role="assistant", content=["Hi"])
    reply.metrics = {"e2e_latency": 1.234, "llm_node_ttft": 0.5}

    for item in (caller, reply):
        latencies.on_conversation_item_added(SimpleNamespace(item=item))

    assert latencies.turns == [
        {
            "end_of_turn_delay": 400,
            "transcription_delay": 200,
            "llm_node_ttft": 500,
            "e2e_latency": 1234,
        }
    ]


def test_replies_the_caller_talked_over_are_counted():
    latencies = TurnLatencies()
    heard = ChatMessage(role="assistant", content=["Hi"])
    cut_off = ChatMessage(role="assistant", content=["Your booking"], interrupted=True)

    for item in (heard, cut_off):
        latencies.on_conversation_item_added(SimpleNamespace(item=item))

    assert latencies.interruptions == 1


def test_a_spoken_line_gets_a_speech_to_text_span_from_livekits_timings(spans):
    caller = ChatMessage(role="user", content=["This Monday please."])
    caller.metrics = {"stopped_speaking_at": 100.0, "transcription_delay": 0.45}
    typed = ChatMessage(role="user", content=["11 am"])

    for item in (caller, typed):
        TurnLatencies().on_conversation_item_added(SimpleNamespace(item=item))

    (stt,) = spans.get_finished_spans()
    assert stt.name == "stt"
    assert (stt.end_time - stt.start_time) / 1e9 == pytest.approx(0.45)
    assert stt.attributes["langfuse.observation.output"] == "This Monday please."


async def test_requests_carry_the_current_trace_to_the_api(spans):
    request = httpx.Request("GET", "http://api/runtime/agents/a1")

    with tracer.start_as_current_span("llm_node") as span:
        await add_trace_context(request)

    trace_id = format(span.get_span_context().trace_id, "032x")
    assert request.headers["traceparent"].startswith(f"00-{trace_id}-")


def test_turn_handling_comes_from_settings():
    options = build_turn_handling(
        Settings(endpointing_mode="fixed", min_endpointing_delay=0.3, preemptive_generation=False)
    )

    assert options["endpointing"] == {"mode": "fixed", "min_delay": 0.3, "max_delay": 2.0}
    assert options["preemptive_generation"] == {"enabled": False}

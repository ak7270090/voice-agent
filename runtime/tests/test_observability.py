from types import SimpleNamespace

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from livekit.agents.llm import ChatMessage

from studio_runtime.config import Settings
from studio_runtime.observability import (
    TurnLatencies,
    create_tracer_provider,
    llm_call_attributes,
)
from studio_runtime.providers import build_turn_handling


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


def test_turn_handling_comes_from_settings():
    options = build_turn_handling(
        Settings(endpointing_mode="fixed", min_endpointing_delay=0.3, preemptive_generation=False)
    )

    assert options["endpointing"] == {"mode": "fixed", "min_delay": 0.3, "max_delay": 2.0}
    assert options["preemptive_generation"] == {"enabled": False}

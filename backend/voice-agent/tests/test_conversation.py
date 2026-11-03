import pytest
from langchain_core.messages import AIMessageChunk, ToolMessage
from livekit.agents import ChatContext

from studio_voice.config import Settings
from studio_voice.conversation import SpokenReplyGraph, build_transcript, create_chat_model


@pytest.mark.parametrize(
    ("llm_model", "effort", "expected"),
    [
        ("openai:gpt-5.4-mini", "none", "none"),
        ("openai:gpt-5.4-mini", "", None),
        ("openai:gpt-4.1-mini", "none", None),
    ],
)
def test_reasoning_effort_applies_only_to_openai_reasoning_models(
    monkeypatch, llm_model, effort, expected
):
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    model = create_chat_model(
        llm_model, Settings(llm_reasoning_effort=effort, llm_timeout_seconds=7)
    )

    assert model.reasoning_effort == expected
    assert model.request_timeout == 7
    assert model.max_retries == 0


class FakeGraph:
    def __init__(self, items: list) -> None:
        self.items = items

    async def astream(self, state, *args, **kwargs):
        for item in self.items:
            yield item


async def test_only_model_text_reaches_the_voice():
    spoken = AIMessageChunk(content="Opening hours are nine to five.")
    graph = SpokenReplyGraph(
        FakeGraph(
            [
                (ToolMessage(content='{"hours": "9-5"}', tool_call_id="1"), {}),
                (AIMessageChunk(content=""), {}),
                (spoken, {}),
            ]
        )
    )

    items = [item async for item in graph.astream({"messages": []})]

    assert items == [(spoken, {})]


def test_transcript_keeps_user_and_agent_text_in_order():
    history = ChatContext.empty()
    history.add_message(role="system", content="instructions")
    history.add_message(role="assistant", content="Hello!")
    history.add_message(role="user", content="When do you open?")
    history.add_message(role="assistant", content="")

    turns = [(turn.role, turn.text) for turn in build_transcript(history)]

    assert turns == [("assistant", "Hello!"), ("user", "When do you open?")]

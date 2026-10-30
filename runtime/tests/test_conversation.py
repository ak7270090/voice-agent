from langchain_core.messages import AIMessageChunk, ToolMessage
from livekit.agents import ChatContext

from studio_runtime.conversation import SpokenReplyGraph, build_transcript


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

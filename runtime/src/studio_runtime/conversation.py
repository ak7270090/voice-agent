"""The LangGraph agent that writes replies, behind LiveKit's LangChain adapter.

The system prompt comes from the LiveKit `Agent` instructions, which `LLMAdapter` passes in as a
system message, so the graph itself has none.
"""

from collections.abc import AsyncIterator
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from livekit.agents import ChatContext
from livekit.plugins.langchain import LLMAdapter

from studio_runtime.config import Settings
from studio_runtime.control_plane import TranscriptTurn

TRANSCRIPT_ROLES = ("user", "assistant")
OPENAI_PROVIDER = "openai"
# OpenAI's reasoning models: they think before answering unless told otherwise.
OPENAI_REASONING_MODEL_PREFIX = "gpt-5"


def create_chat_model(llm_model: str, settings: Settings) -> BaseChatModel:
    """The agent's model from its "provider:model" string. A voice turn only picks a step's tool
    or writes a sentence, so a reasoning model's thinking (time before the first word) is set
    by `llm_reasoning_effort` ("none" skips it); other models take no such option."""
    provider, _, model = llm_model.partition(":")
    # A request that stalls is cut off and retried by FlowGraph (one took 31 s in a scenario
    # run while the next took 1 s); the client's own hidden retries would only add waiting.
    options: dict[str, object] = {"timeout": settings.llm_timeout_seconds, "max_retries": 0}
    if (
        settings.llm_reasoning_effort
        and provider == OPENAI_PROVIDER
        and model.startswith(OPENAI_REASONING_MODEL_PREFIX)
    ):
        options["reasoning_effort"] = settings.llm_reasoning_effort
    return init_chat_model(llm_model, **options)


def build_conversation_graph(
    llm_model: str, tools: list[BaseTool], settings: Settings
) -> CompiledStateGraph:
    # Errors are raised, not spoken: the middleware's default would hand the error text to the
    # voice. A dropped connection mid-reply otherwise left half a sentence (clinic-voice-agent).
    retry = ModelRetryMiddleware(
        max_retries=settings.llm_max_retries,
        initial_delay=settings.llm_retry_delay_seconds,
        on_failure="error",
    )
    model = create_chat_model(llm_model, settings)
    return create_agent(model=model, tools=tools, middleware=[retry])


class SpokenReplyGraph:
    """Passes only the model's own text to LiveKit, so tool results are never read aloud.

    In `messages` stream mode LangGraph also emits the tools node's ToolMessages, and
    LLMAdapter turns anything with string content into speech.
    """

    def __init__(self, graph: CompiledStateGraph) -> None:
        self._graph = graph

    async def astream(self, state: dict, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        async for item in self._graph.astream(state, *args, **kwargs):
            if is_spoken_model_text(item):
                yield item


def is_spoken_model_text(item: Any) -> bool:
    """True for (token, metadata) pairs whose token is text from the model."""
    token = item[0] if isinstance(item, tuple) and len(item) == 2 else item
    return isinstance(token, AIMessageChunk) and bool(token.text)


def create_llm(
    llm_model: str,
    tools: list[BaseTool],
    settings: Settings,
    callbacks: list[BaseCallbackHandler] | None = None,
) -> LLMAdapter:
    return LLMAdapter(
        SpokenReplyGraph(build_conversation_graph(llm_model, tools, settings)),
        config={"callbacks": callbacks or []},
    )


def build_transcript(history: ChatContext) -> list[TranscriptTurn]:
    return [
        TranscriptTurn(role=item.role, text=item.text_content)
        for item in history.items
        if item.type == "message" and item.role in TRANSCRIPT_ROLES and item.text_content
    ]

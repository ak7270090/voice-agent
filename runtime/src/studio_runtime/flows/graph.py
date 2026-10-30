"""Stands in for a LangGraph graph behind LiveKit's LLMAdapter and runs one caller turn.

Each pass gives the LLM the current step's prompt and only that step's tools. When a tool moves
the flow, the next pass answers from the new step, so the reply always comes from where the
conversation now is.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from studio_runtime.flows import prompts
from studio_runtime.flows.runner import FlowRunner

logger = logging.getLogger(__name__)

# Model calls in one turn: tool calls, a move, then the reply.
MAX_PASSES = 6


def spoken(text: str) -> tuple[AIMessageChunk, dict]:
    """The (token, metadata) pair LLMAdapter expects from a graph in "messages" mode."""
    return AIMessageChunk(content=text), {}


class FlowGraph:
    def __init__(
        self,
        runner: FlowRunner,
        model: BaseChatModel,
        base_instructions: str,
        max_retries: int,
    ) -> None:
        self._runner = runner
        self._model = model
        self._base_instructions = base_instructions
        self._max_retries = max_retries

    async def astream(self, state: dict, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        runner = self._runner
        if runner.ended:
            return
        history = [m for m in state.get("messages", []) if not isinstance(m, SystemMessage)]
        users = [m for m in history if isinstance(m, HumanMessage)]
        if users:
            await runner.take_answer(users[-1].text)
        scratch: list[BaseMessage] = []
        for _ in range(MAX_PASSES):
            if runner.ended:
                if runner.final_message:
                    yield spoken(runner.final_message)
                return
            tools = runner.tools()
            model = self._model.bind_tools(tools) if tools else self._model
            messages = [SystemMessage(runner.system_prompt(self._base_instructions))]
            reply = None
            async for chunk in self._stream(model, messages + history + scratch):
                if chunk.text:
                    yield spoken(chunk.text)
                reply = chunk if reply is None else reply + chunk
            if reply is None or not reply.tool_calls:
                return
            scratch.append(AIMessage(content=reply.text, tool_calls=reply.tool_calls))
            runner.moved = False
            by_name = {tool.name: tool for tool in tools}
            for call in reply.tool_calls:
                tool = by_name.get(call["name"])
                if tool is None:
                    result = prompts.UNKNOWN_TOOL.format(name=call["name"])
                else:
                    result = await tool.ainvoke(call["args"])
                scratch.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
                if runner.moved:
                    break
            if runner.moved:
                # The new step starts clean; what it needs is in its prompt.
                scratch = []

    async def _stream(self, model, messages: list[BaseMessage]) -> AsyncIterator[AIMessageChunk]:
        """Retries a model call that fails before saying anything (a dropped connection)."""
        for attempt in range(self._max_retries + 1):
            started = False
            try:
                async for chunk in model.astream(messages):
                    started = True
                    yield chunk
                return
            except Exception:
                if started or attempt == self._max_retries:
                    raise
                logger.warning("model call failed; retrying", exc_info=True)

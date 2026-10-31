"""Stands in for a LangGraph graph behind LiveKit's LLMAdapter and runs one caller turn.

Each pass gives the LLM the current step's prompt and only that step's tools. When a tool moves
the flow, the next pass answers from the new step, so the reply always comes from where the
conversation now is. To keep the caller from waiting in silence:
- a reply written alongside `save_fields` (nothing moved) is the turn's answer: no second call;
- a step's "say on entering" line is spoken as soon as the flow arrives there;
- a slow tool's "say while it runs" line is spoken inside the same reply (a separate
  `session.say()` dropped replies in clinic-voice-agent);
- a tool whose service gives no answer gets a fixed apology from code, never a guess.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool

from studio_runtime.flows import prompts
from studio_runtime.flows.runner import SAVE_FIELDS_TOOL, FlowRunner
from studio_runtime.observability import FLOW_STEP_KEY

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
        filler_delay_seconds: float = 0.7,
        callbacks: list[BaseCallbackHandler] | None = None,
    ) -> None:
        self._runner = runner
        self._model = model
        self._base_instructions = base_instructions
        self._max_retries = max_retries
        self._filler_delay_seconds = filler_delay_seconds
        self._callbacks = callbacks or []

    async def astream(self, state: dict, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        runner = self._runner
        if runner.ended:
            # The caller spoke over the end message (or after it): say it again; the call
            # hangs up once it has been heard in full.
            if runner.final_message:
                yield spoken(runner.final_message)
            return
        history = [m for m in state.get("messages", []) if not isinstance(m, SystemMessage)]
        users = [m for m in history if isinstance(m, HumanMessage)]
        if users:
            runner.entry_line = ""
            await runner.take_answer(users[-1].text)
        scratch: list[BaseMessage] = []
        filler_said = False
        for _ in range(MAX_PASSES):
            if runner.ended:
                if runner.final_message:
                    yield spoken(runner.final_message)
                return
            if runner.entry_line:
                yield spoken(f"{runner.entry_line} ")
                history = [*history, AIMessage(content=runner.entry_line)]
                runner.entry_line = ""
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
            for group in tool_call_groups(reply.tool_calls, runner):
                results = asyncio.gather(*(self._run_tool(by_name, call) for call in group))
                fillers = (runner.filler_for(call["name"]) for call in group)
                filler = "" if filler_said else next((line for line in fillers if line), "")
                if filler and not await self._finishes_quickly(results):
                    yield spoken(f"{filler} ")
                    filler_said = True
                for call, result in zip(group, await results, strict=True):
                    scratch.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
                if runner.failure_line:
                    yield spoken(f"{runner.failure_line} ")
                    runner.failure_line = ""
                if runner.moved:
                    break
            if runner.moved:
                # The new step starts clean; what it needs is in its prompt.
                scratch = []
            elif reply.text and only_saved_fields(reply.tool_calls):
                return

    async def _run_tool(self, tools: dict[str, BaseTool], call: dict) -> Any:
        tool = tools.get(call["name"])
        if tool is None:
            return prompts.UNKNOWN_TOOL.format(name=call["name"])
        return await tool.ainvoke(call["args"], config=self._config())

    async def _finishes_quickly(self, task: asyncio.Future) -> bool:
        done, _ = await asyncio.wait({task}, timeout=self._filler_delay_seconds)
        return bool(done)

    def _config(self) -> dict:
        """LangChain config for each model and tool call: the tracer, and the step for its span."""
        step = self._runner.current.id if self._runner.current else ""
        return {"callbacks": self._callbacks, "metadata": {FLOW_STEP_KEY: step}}

    async def _stream(self, model, messages: list[BaseMessage]) -> AsyncIterator[AIMessageChunk]:
        """Retries a model call that fails before saying anything (a dropped connection)."""
        config = self._config()
        for attempt in range(self._max_retries + 1):
            started = False
            try:
                async for chunk in model.astream(messages, config=config):
                    started = True
                    yield chunk
                return
            except Exception:
                if started or attempt == self._max_retries:
                    raise
                logger.warning("model call failed; retrying", exc_info=True)


def tool_call_groups(tool_calls: list[dict], runner: FlowRunner) -> list[list[dict]]:
    """Calls that look things up or save fields run together, so two slow lookups take as long
    as one. A move changes the step, so then each call runs alone, in order, and a move stops
    the rest (the new step decides what happens next)."""
    if any(runner.is_move(call["name"]) for call in tool_calls):
        return [[call] for call in tool_calls]
    return [tool_calls]


def only_saved_fields(tool_calls: list[dict]) -> bool:
    return all(call["name"] == SAVE_FIELDS_TOOL for call in tool_calls)

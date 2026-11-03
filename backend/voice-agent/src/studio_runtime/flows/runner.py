"""The flow's state for one call: where it is, what was collected, and what tools returned.

Moves between steps are made by code: the LLM picks a condition by calling its tool, and
"all fields collected" or a tool's success or failure moves without asking it.
"""

import asyncio
import json
import re
import time
from collections.abc import Callable, Coroutine
from datetime import date
from typing import Any, TypeVar

import httpx
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import Field, create_model

from studio_runtime.flows import calcom, prompts
from studio_runtime.flows.http_tools import (
    MAX_TEXT_RESULT_CHARS,
    ToolResult,
    call_tool,
    fill_leniently,
    mask_secrets,
    placeholders,
)
from studio_runtime.flows.schema import (
    EndNode,
    FieldSpec,
    Flow,
    FlowEdge,
    GlobalNode,
    StartNode,
    StepNode,
    ToolNode,
    TransferNode,
)
from studio_runtime.observability import (
    LANGFUSE_OBSERVATION_TYPE,
    TOOL_OBSERVATION,
    flow_span,
    set_span_output,
)

CONDITION_EDGE = "condition"
FIELDS_COMPLETE_EDGE = "fields_complete"
SUCCESS_EDGE = "success"
FAILURE_EDGE = "failure"
ALWAYS_EDGE = "always"
TRANSFER_OUTCOME = "transfer_requested"
TOOL_FAILED_OUTCOME = "tool_failed"
DATE_FIELD = "date"
SAVE_FIELDS_TOOL = "save_fields"
MAX_AUTOMATIC_MOVES = 20
# Who moved the flow, shown on each flow.move span.
MOVED_BY_START = "start"
MOVED_BY_LLM = "llm"
MOVED_BY_CODE = "code"
# Who started a tool call, in the call record: a tool node on the path, or the LLM.
CALLED_BY_FLOW = "flow"
CALLED_BY_LLM = "llm"
MAX_LOGGED_RESULT_CHARS = 500

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

FieldParsers = dict[str, Callable[[str, date], Any]]
T = TypeVar("T")


def value_at(data: dict, path: str) -> Any:
    """The value at a dot path such as "doctor" or "booking.id"; None when it is missing."""
    value: Any = data
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def spoken_value(value: Any) -> Any:
    """An ISO date ("2026-11-02") as people say it ("Monday 2 November"); the rest unchanged."""
    if isinstance(value, str) and ISO_DATE.fullmatch(value):
        day = date.fromisoformat(value)
        return f"{day:%A} {day.day} {day:%B}"
    return value


def shown_to_llm(node: ToolNode, data: Any) -> Any:
    """Only the result fields the tool names, if any: a shorter prompt is faster and gives the
    model less to misread. Fields and end messages still get the whole result."""
    if not node.data.result_fields or not isinstance(data, dict):
        return data
    return {path: value_at(data, path) for path in node.data.result_fields}


async def finish_even_if_interrupted(work: Coroutine[Any, Any, T]) -> T:
    """Runs `work` to the end even if the awaiting turn is cancelled (the caller cut in); the
    turn still stops, but the work and its state change complete in the background."""
    return await asyncio.shield(asyncio.ensure_future(work))


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "next"


class FlowRunner:
    def __init__(
        self,
        flow: Flow,
        http: httpx.AsyncClient,
        parsers: FieldParsers,
        today: date,
        knowledge_tool: BaseTool | None = None,
        tool_unavailable_line: str = "",
        idempotency_prefix: str = "",
        on_change: Callable[["FlowRunner"], None] | None = None,
        call_values: dict[str, Any] | None = None,
        secrets: dict[str, str] | None = None,
    ) -> None:
        self._idempotency_prefix = idempotency_prefix
        self._secrets = secrets or {}
        self._nodes = {node.id: node for node in flow.nodes}
        self._edges = flow.edges
        self._http = http
        self._parsers = parsers
        self._today = today
        self._knowledge_tool = knowledge_tool
        self._tool_unavailable_line = tool_unavailable_line
        self._on_change = on_change
        # Known before the first step (the caller's number): tools use them like fields.
        self.fields: dict[str, Any] = dict(call_values or {})
        # Every tool call, in order, for the call record.
        self.tool_calls: list[dict[str, Any]] = []
        self.results: dict[str, Any] = {}
        self.last_result: tuple[str, Any] | None = None
        self._last_result_for_llm: tuple[str, Any] | None = None
        self.path: list[str] = []
        self.current: StepNode | None = None
        self.ended = False
        self.outcome: str | None = None
        self.final_message = ""
        # A Transfer node's number or sip: address, handed the caller after its message.
        self.transfer_to = ""
        self.moved = False
        # A step's "say on entering" line, waiting to be spoken by the graph.
        self.entry_line = ""
        # Said by the graph when a tool's service gave no answer.
        self.failure_line = ""
        # The flow came back to a step it had left: an action failed (a slot just taken) or the
        # caller wants to change something. Its fields are still filled in, so until the caller
        # speaks again the step does not move on; re-saving them would only read the same
        # details back. `returned_after_failure` says which, for the prompt.
        self.holding = False
        self.returned_after_failure = False
        self._move_targets: dict[str, str] = {}

    async def start(self) -> None:
        start = next(node for node in self._nodes.values() if isinstance(node, StartNode))
        self.path.append(start.id)
        await self.enter(self._outgoing(start.id)[0].target, moved_by=MOVED_BY_START)

    async def aclose(self) -> None:
        await self._http.aclose()

    def _outgoing(self, node_id: str, kind: str | None = None) -> list[FlowEdge]:
        return [
            edge
            for edge in self._edges
            if edge.source == node_id and (kind is None or edge.kind == kind)
        ]

    def _notify(self) -> None:
        if self._on_change is not None:
            self._on_change(self)

    async def enter(self, node_id: str, moved_by: str = MOVED_BY_LLM) -> None:
        """Runs tool nodes on the way and stops at the next step, end or transfer.

        Once started, a move finishes even if the caller talks over the agent and LiveKit
        cancels the turn: a booking on the way must not be cut off halfway, and the flow's state
        must say whether it happened. The next turn then answers from that state."""
        await finish_even_if_interrupted(self._enter(node_id, moved_by))

    async def _enter(self, node_id: str, moved_by: str) -> None:
        self.moved = True
        start = len(self.path)
        source = self.current.id if self.current else None
        with flow_span("flow.move", {"from": source, "moved_by": moved_by}) as span:
            after_failure = False
            for _ in range(MAX_AUTOMATIC_MOVES):
                node = self._nodes[node_id]
                self.path.append(node.id)
                if isinstance(node, StepNode):
                    self.current = node
                    # Back at a step that collects details: no opening line again ("Sure, I can
                    # help with that." twice); the LLM says what happens next, told why it is
                    # back by its prompt. A step without fields (a read-back) speaks again.
                    came_back = after_failure or node.id in self.path[:-1]
                    returned = came_back and bool(node.data.fields)
                    self.holding = returned
                    self.returned_after_failure = after_failure
                    line = "" if returned else node.data.say_on_enter
                    self.entry_line = fill_leniently(line, self.message_values())
                    break
                if isinstance(node, EndNode | TransferNode):
                    self._finish(node)
                    break
                if isinstance(node, ToolNode):
                    next_edge = await self._run_path_tool(node)
                    if next_edge is None:
                        self.ended, self.outcome = True, TOOL_FAILED_OUTCOME
                        break
                    after_failure = next_edge.kind == FAILURE_EDGE
                    node_id = next_edge.target
            set_span_output(span, {"to": self.path[-1], "through": self.path[start:]})
        self._notify()

    def _finish(self, node: EndNode | TransferNode) -> None:
        self.ended = True
        if isinstance(node, EndNode):
            self.outcome = node.data.outcome
        else:
            self.outcome = TRANSFER_OUTCOME
            self.transfer_to = node.data.destination
        self.final_message = fill_leniently(node.data.message, self.message_values())

    def message_values(self) -> dict[str, Any]:
        """Values for {placeholders} in spoken lines: the fields, then the latest tool result
        (the service's answer wins), with dates said the way people say them."""
        values = dict(self.fields)
        if self.last_result and isinstance(self.last_result[1], dict):
            values.update(self.last_result[1])
        return {name: spoken_value(value) for name, value in values.items()}

    async def _run_path_tool(self, node: ToolNode) -> FlowEdge | None:
        """A tool node on the path runs without the LLM, so it gets its tool span here."""
        with flow_span(node.data.name, self.fields) as span:
            span.set_attribute(LANGFUSE_OBSERVATION_TYPE, TOOL_OBSERVATION)
            result = await self._timed_call(node, self.fields, CALLED_BY_FLOW)
            set_span_output(span, {"ok": result.ok, "result": result.data})
        self._record(node, result)
        wanted = SUCCESS_EDGE if result.ok else FAILURE_EDGE
        edges = self._outgoing(node.id, wanted) or self._outgoing(node.id, ALWAYS_EDGE)
        return edges[0] if edges else None

    def _idempotency_key(self, node: ToolNode) -> str | None:
        """The same for every attempt of one tool in one call, so the service books once."""
        return f"{self._idempotency_prefix}:{node.id}" if self._idempotency_prefix else None

    def _record(self, node: ToolNode, result: ToolResult) -> None:
        self.results[node.data.name] = result.data
        self.last_result = (node.data.name, result.data)
        self._last_result_for_llm = (node.data.name, shown_to_llm(node, result.data))
        if result.ok and isinstance(result.data, dict):
            for field, path in node.data.save_to_fields.items():
                value = value_at(result.data, path)
                if value is not None:
                    self.fields[field] = value
        self._notify()

    def is_move(self, tool_name: str) -> bool:
        """True for a step's go_to_… tools (known once `tools()` has built them this pass)."""
        return tool_name in self._move_targets

    def filler_for(self, tool_name: str) -> str:
        """What to say while this tool call runs: an attached tool's own line, or the line of
        the tool node a move leads into."""
        target = self._move_targets.get(tool_name)
        for node in self._nodes.values():
            if not isinstance(node, ToolNode):
                continue
            if node.data.name == tool_name or node.id == target:
                return node.data.say_while_running
        return ""

    # Fields

    def _step_fields(self) -> list[FieldSpec]:
        return self.current.data.fields if self.current else []

    def missing_fields(self) -> list[FieldSpec]:
        return [f for f in self._step_fields() if f.required and f.name not in self.fields]

    def _normalise(self, field: FieldSpec, raw: Any) -> Any:
        parser = self._parsers.get(field.type)
        if parser is None:
            return str(raw).strip() or None
        return parser(str(raw), self._today)

    def _spec(self, name: str) -> FieldSpec:
        """The field of that name in any step, so tool arguments are read like answers."""
        for node in self._nodes.values():
            if isinstance(node, StepNode):
                for field in node.data.fields:
                    if field.name == name:
                        return field
        return FieldSpec(name=name)

    async def save_fields(self, values: dict[str, Any]) -> str:
        with flow_span("flow.save_fields", values) as span:
            specs = {field.name: field for field in self._step_fields()}
            problems = []
            for name, raw in values.items():
                if raw in (None, "") or name not in specs:
                    continue
                value = self._normalise(specs[name], raw)
                if value is None:
                    problems.append(prompts.COULD_NOT_READ.format(name=name, value=raw))
                else:
                    self.fields[name] = value
            self._notify()
            moved = await self._move_if_complete()
            missing = ", ".join(field.name for field in self.missing_fields())
            status = (
                prompts.ALL_COLLECTED if not missing else prompts.STILL_NEEDED.format(names=missing)
            )
            result = " ".join([prompts.SAVED, status, *problems] + ([moved] if moved else []))
            set_span_output(span, result)
        return result

    async def take_answer(self, user_text: str) -> None:
        """Reads the next missing typed field from the caller's own words before the LLM runs,
        so an answer counts even when the LLM forgets to save it (clinic-voice-agent's fix)."""
        # The caller has spoken since the flow came back: the step may move on again.
        self.holding = False
        missing = self.missing_fields()
        if not missing or missing[0].type not in self._parsers:
            return
        field = missing[0]
        with flow_span("flow.take_answer", {"field": field.name, "words": user_text}) as span:
            value = self._normalise(field, user_text)
            set_span_output(span, {field.name: value})
            if value is not None:
                self.fields[field.name] = value
                self._notify()
                await self._move_if_complete()

    async def _move_if_complete(self) -> str | None:
        if self.current is None or self.missing_fields() or self.holding:
            return None
        edges = self._outgoing(self.current.id, FIELDS_COMPLETE_EDGE)
        if not edges:
            return None
        await self.enter(edges[0].target, moved_by=MOVED_BY_CODE)
        return prompts.MOVED.format(target=self.label(edges[0].target))

    # What the LLM sees

    def label(self, node_id: str) -> str:
        node = self._nodes[node_id]
        if isinstance(node, StepNode | GlobalNode):
            return node.data.name
        if isinstance(node, EndNode):
            return node.data.outcome
        if isinstance(node, ToolNode):
            return node.data.name
        return node.type

    def system_prompt(self, base_instructions: str) -> str:
        step = self.current
        sections = [
            base_instructions,
            prompts.STEP_SECTION.format(
                today=f"{self._today:%A %d %B %Y}",
                step_name=step.data.name,
                step_instructions=step.data.instructions,
            ),
        ]
        if step.data.fields:
            lines = "\n".join(self._field_line(field) for field in step.data.fields)
            sections.append(prompts.FIELDS_SECTION.format(lines=lines))
        if self._last_result_for_llm is not None:
            name, data = self._last_result_for_llm
            result = json.dumps(data, default=str)[:MAX_TEXT_RESULT_CHARS]
            sections.append(prompts.RESULTS_SECTION.format(tool=name, result=result))
        if self.holding and self.returned_after_failure:
            sections.append(prompts.AFTER_FAILURE.format(tool=self._last_result_for_llm[0]))
        elif self.holding:
            sections.append(prompts.BACK_TO_CHANGE)
        moves = [(tool.name, condition) for tool, condition in self._move_tools()]
        if moves:
            lines = "\n".join(prompts.MOVE_LINE.format(tool=n, condition=c) for n, c in moves)
            sections.append(prompts.MOVES_SECTION.format(lines=lines))
        return "\n\n".join(sections)

    def _field_line(self, field: FieldSpec) -> str:
        description = field.description or field.type
        if field.name not in self.fields:
            return prompts.FIELD_MISSING.format(name=field.name, description=description)
        value = self.fields[field.name]
        if field.type == DATE_FIELD:
            value = f"{value} ({date.fromisoformat(value):%A})"
        return prompts.FIELD_HAVE.format(name=field.name, description=description, value=value)

    def tools(self) -> list[BaseTool]:
        """Only the current step's tools: its fields, its moves, the global moves, the tools
        attached to it, and knowledge search if the step uses it."""
        step = self.current
        tools: list[BaseTool] = []
        if step.data.fields:
            tools.append(self._save_fields_tool())
        tools += [tool for tool, _ in self._move_tools()]
        tools += [self._attached_tool(self._nodes[tool_id]) for tool_id in step.data.tools]
        if step.data.use_knowledge and self._knowledge_tool is not None:
            tools.append(self._knowledge_tool)
        return tools

    def _save_fields_tool(self) -> BaseTool:
        arguments = {
            field.name: (str | None, Field(default=None, description=field.description))
            for field in self._step_fields()
        }
        schema = create_model("SaveFieldsArgs", **arguments)

        async def save(**values: Any) -> str:
            return await self.save_fields(values)

        return StructuredTool.from_function(
            coroutine=save,
            name=SAVE_FIELDS_TOOL,
            description=prompts.SAVE_FIELDS_DESCRIPTION,
            args_schema=schema,
        )

    def _move_tools(self) -> list[tuple[BaseTool, str]]:
        moves = [
            (edge.target, edge.condition)
            for edge in self._outgoing(self.current.id, CONDITION_EDGE)
        ]
        for node in self._nodes.values():
            if isinstance(node, GlobalNode) and self._outgoing(node.id):
                moves.append((self._outgoing(node.id)[0].target, node.data.condition))
        tools, names = [], set()
        for target, condition in moves:
            name = f"go_to_{slug(self.label(target))}"
            while name in names:
                name += "_"
            names.add(name)
            self._move_targets[name] = target
            tools.append((self._move_tool(name, target, condition), condition))
        return tools

    def _move_tool(self, name: str, target: str, condition: str) -> BaseTool:
        async def move() -> str:
            await self.enter(target)
            return prompts.MOVED.format(target=self.label(target))

        return StructuredTool.from_function(coroutine=move, name=name, description=condition)

    async def _call_and_record(self, node: ToolNode, given: dict[str, Any]) -> ToolResult:
        result = await self._timed_call(node, {**self.fields, **given}, CALLED_BY_LLM)
        self._record(node, result)
        return result

    async def _timed_call(self, node: ToolNode, values: dict[str, Any], by: str) -> ToolResult:
        """Calls the tool and logs it for the call record: what ran, who asked, how it went."""
        started_at, started = time.time(), time.perf_counter()
        if node.data.kind in calcom.KINDS:
            found = await calcom.call_calcom(self._http, node.data, values, self._secrets)
            result = ToolResult(
                found.ok, mask_secrets(found.data, self._secrets), found.unavailable
            )
        else:
            result = await call_tool(
                self._http, node.data, values, self._idempotency_key(node), self._secrets
            )
        self.tool_calls.append(
            {
                "name": node.data.name,
                "by": by,
                "at": started_at,
                "ms": round((time.perf_counter() - started) * 1000),
                "ok": result.ok,
                "unavailable": result.unavailable,
                "result": json.dumps(result.data, default=str)[:MAX_LOGGED_RESULT_CHARS],
            }
        )
        return result

    def _attached_tool(self, node: ToolNode) -> BaseTool:
        names = (
            calcom.inputs(node.data) if node.data.kind in calcom.KINDS else placeholders(node.data)
        )
        arguments = {name: (str | None, Field(default=None)) for name in names}
        schema = create_model(f"{node.data.name}_args", **arguments)

        async def run(**values: Any) -> str:
            given = {
                name: self._normalise(self._spec(name), value) or value
                for name, value in values.items()
                if value not in (None, "")
            }
            result = await finish_even_if_interrupted(self._call_and_record(node, given))
            if result.unavailable:
                # Said by code, word for word; the LLM is told not to guess.
                self.failure_line = self._tool_unavailable_line
                return prompts.TOOL_UNAVAILABLE.format(name=node.data.name)
            shown = shown_to_llm(node, result.data)
            return json.dumps(shown, default=str)[:MAX_TEXT_RESULT_CHARS]

        return StructuredTool.from_function(
            coroutine=run,
            name=node.data.name,
            description=node.data.description or node.data.name,
            args_schema=schema,
        )

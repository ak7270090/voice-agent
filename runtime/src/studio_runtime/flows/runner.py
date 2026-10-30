"""The flow's state for one call: where it is, what was collected, and what tools returned.

Moves between steps are made by code: the LLM picks a condition by calling its tool, and
"all fields collected" or a tool's success or failure moves without asking it.
"""

import json
import re
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import Field, create_model

from studio_runtime.flows import prompts
from studio_runtime.flows.http_tools import (
    MAX_TEXT_RESULT_CHARS,
    ToolResult,
    call_tool,
    fill_leniently,
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

FieldParsers = dict[str, Callable[[str, date], Any]]


def value_at(data: dict, path: str) -> Any:
    """The value at a dot path such as "doctor" or "booking.id"; None when it is missing."""
    value: Any = data
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


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
        knowledge_rule: str = "",
        on_change: Callable[["FlowRunner"], None] | None = None,
    ) -> None:
        self._nodes = {node.id: node for node in flow.nodes}
        self._edges = flow.edges
        self._http = http
        self._parsers = parsers
        self._today = today
        self._knowledge_tool = knowledge_tool
        self._knowledge_rule = knowledge_rule
        self._on_change = on_change
        self.fields: dict[str, Any] = {}
        self.results: dict[str, Any] = {}
        self.last_result: tuple[str, Any] | None = None
        self.path: list[str] = []
        self.current: StepNode | None = None
        self.ended = False
        self.outcome: str | None = None
        self.final_message = ""
        self.moved = False
        # A step's "say on entering" line, waiting to be spoken by the graph.
        self.entry_line = ""
        self._move_targets: dict[str, str] = {}

    async def start(self) -> None:
        start = next(node for node in self._nodes.values() if isinstance(node, StartNode))
        self.path.append(start.id)
        await self.enter(self._outgoing(start.id)[0].target)

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

    async def enter(self, node_id: str) -> None:
        """Runs tool nodes on the way and stops at the next step, end or transfer."""
        self.moved = True
        for _ in range(MAX_AUTOMATIC_MOVES):
            node = self._nodes[node_id]
            self.path.append(node.id)
            if isinstance(node, StepNode):
                self.current = node
                self.entry_line = node.data.say_on_enter
                break
            if isinstance(node, EndNode | TransferNode):
                self._finish(node)
                break
            if isinstance(node, ToolNode):
                next_edge = await self._run_path_tool(node)
                if next_edge is None:
                    self.ended, self.outcome = True, TOOL_FAILED_OUTCOME
                    break
                node_id = next_edge.target
        self._notify()

    def _finish(self, node: EndNode | TransferNode) -> None:
        self.ended = True
        if isinstance(node, EndNode):
            self.outcome = node.data.outcome
        else:
            self.outcome = TRANSFER_OUTCOME
        self.final_message = fill_leniently(node.data.message, self.message_values())

    def message_values(self) -> dict[str, Any]:
        values = dict(self.fields)
        if self.last_result and isinstance(self.last_result[1], dict):
            values.update(self.last_result[1])
        return values

    async def _run_path_tool(self, node: ToolNode) -> FlowEdge | None:
        result = await call_tool(self._http, node.data, self.fields)
        self._record(node, result)
        wanted = SUCCESS_EDGE if result.ok else FAILURE_EDGE
        edges = self._outgoing(node.id, wanted) or self._outgoing(node.id, ALWAYS_EDGE)
        return edges[0] if edges else None

    def _record(self, node: ToolNode, result: ToolResult) -> None:
        self.results[node.data.name] = result.data
        self.last_result = (node.data.name, result.data)
        if result.ok and isinstance(result.data, dict):
            for field, path in node.data.save_to_fields.items():
                value = value_at(result.data, path)
                if value is not None:
                    self.fields[field] = value
        self._notify()

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
        return " ".join([prompts.SAVED, status, *problems] + ([moved] if moved else []))

    async def take_answer(self, user_text: str) -> None:
        """Reads the next missing typed field from the caller's own words before the LLM runs,
        so an answer counts even when the LLM forgets to save it (clinic-voice-agent's fix)."""
        missing = self.missing_fields()
        if not missing or missing[0].type not in self._parsers:
            return
        value = self._normalise(missing[0], user_text)
        if value is not None:
            self.fields[missing[0].name] = value
            self._notify()
            await self._move_if_complete()

    async def _move_if_complete(self) -> str | None:
        if self.current is None or self.missing_fields():
            return None
        edges = self._outgoing(self.current.id, FIELDS_COMPLETE_EDGE)
        if not edges:
            return None
        await self.enter(edges[0].target)
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
        if self.last_result is not None:
            name, data = self.last_result
            result = json.dumps(data, default=str)[:MAX_TEXT_RESULT_CHARS]
            sections.append(prompts.RESULTS_SECTION.format(tool=name, result=result))
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

    def _attached_tool(self, node: ToolNode) -> BaseTool:
        arguments = {name: (str | None, Field(default=None)) for name in placeholders(node.data)}
        schema = create_model(f"{node.data.name}_args", **arguments)

        async def run(**values: Any) -> str:
            given = {
                name: self._normalise(self._spec(name), value) or value
                for name, value in values.items()
                if value not in (None, "")
            }
            result = await call_tool(self._http, node.data, {**self.fields, **given})
            self._record(node, result)
            return json.dumps(result.data, default=str)[:MAX_TEXT_RESULT_CHARS]

        return StructuredTool.from_function(
            coroutine=run,
            name=node.data.name,
            description=node.data.description or node.data.name,
            args_schema=schema,
        )

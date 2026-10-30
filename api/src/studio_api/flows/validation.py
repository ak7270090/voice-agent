"""Checks that a flow can run. A draft may have issues; publishing needs none."""

import re
from collections import defaultdict

from studio_api.flows.constants import (
    ALLOWED_EDGE_KINDS,
    CONDITION_EDGE,
    FIELDS_COMPLETE_EDGE,
    GLOBAL_NODE,
    PLACEHOLDER_PATTERN,
    START_NODE,
    STEP_NODE,
    TOOL_NODE,
)
from studio_api.flows.schemas import Flow, FlowIssue, StepNode, ToolNode

PLACEHOLDER = re.compile(PLACEHOLDER_PATTERN)


def article(word: str) -> str:
    return "An" if word[0] in "aeiou" else "A"


def validate_flow(flow: Flow) -> list[FlowIssue]:
    issues: list[FlowIssue] = []
    nodes = {node.id: node for node in flow.nodes}
    if len(nodes) != len(flow.nodes):
        issues.append(FlowIssue(message="Two nodes share an id"))
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    for edge in flow.edges:
        if edge.source not in nodes or edge.target not in nodes:
            issues.append(FlowIssue(message="Edge points to a missing node", edge_id=edge.id))
            continue
        outgoing[edge.source].append(edge)
        incoming[edge.target].append(edge)

    starts = [node for node in flow.nodes if node.type == START_NODE]
    if len(starts) != 1:
        issues.append(FlowIssue(message="A flow needs exactly one Start node"))
    for node in flow.nodes:
        issues += _check_edges(node, outgoing[node.id], incoming[node.id])
    issues += _check_steps_and_tools(flow, nodes)
    if len(starts) == 1:
        issues += _check_reachable(flow, starts[0].id, outgoing, nodes)
    return issues


def _check_edges(node, outgoing, incoming) -> list[FlowIssue]:
    issues = []
    allowed = ALLOWED_EDGE_KINDS[node.type]
    for edge in outgoing:
        if edge.kind not in allowed:
            message = f"{article(node.type)} {node.type} node cannot have a '{edge.kind}' edge"
            issues.append(FlowIssue(message=message, edge_id=edge.id))
        if edge.kind == CONDITION_EDGE and not edge.condition.strip():
            issues.append(FlowIssue(message="Say when to take this edge", edge_id=edge.id))
        if edge.kind == FIELDS_COMPLETE_EDGE and not any(
            field.required for field in node.data.fields
        ):
            message = "'All fields collected' needs a step with required fields"
            issues.append(FlowIssue(message=message, edge_id=edge.id))
    if node.type in (START_NODE, GLOBAL_NODE):
        if len(outgoing) != 1:
            message = f"{article(node.type)} {node.type} node needs exactly one outgoing edge"
            issues.append(FlowIssue(message=message, node_id=node.id))
        if incoming:
            message = f"Nothing can lead into a {node.type} node"
            issues.append(FlowIssue(message=message, node_id=node.id))
    if node.type == GLOBAL_NODE and not node.data.condition.strip():
        issues.append(FlowIssue(message="Say when this global node fires", node_id=node.id))
    if node.type == TOOL_NODE and incoming and not outgoing:
        message = "A tool in the path needs an edge for what happens next"
        issues.append(FlowIssue(message=message, node_id=node.id))
    return issues


def _check_steps_and_tools(flow: Flow, nodes: dict) -> list[FlowIssue]:
    issues = []
    field_names = {
        field.name
        for node in flow.nodes
        if isinstance(node, StepNode)
        for field in node.data.fields
    }
    tool_names = defaultdict(int)
    for node in flow.nodes:
        if isinstance(node, StepNode):
            names = [field.name for field in node.data.fields]
            if len(names) != len(set(names)):
                issues.append(FlowIssue(message="Two fields share a name", node_id=node.id))
            for tool_id in node.data.tools:
                if not isinstance(nodes.get(tool_id), ToolNode):
                    message = f"Attached tool '{tool_id}' is not a tool node"
                    issues.append(FlowIssue(message=message, node_id=node.id))
        if isinstance(node, ToolNode):
            tool_names[node.data.name] += 1
            if not node.data.url.startswith(("http://", "https://")):
                issues.append(FlowIssue(message="Tool needs an http(s) URL", node_id=node.id))
            templates = [node.data.url, *node.data.body.values()]
            unknown = {
                name for text in templates for name in PLACEHOLDER.findall(text)
            } - field_names
            if unknown and not _attached_anywhere(flow, node.id):
                message = f"Placeholders {sorted(unknown)} are not fields of any step"
                issues.append(FlowIssue(message=message, node_id=node.id))
            not_fields = sorted(set(node.data.save_to_fields) - field_names)
            if not_fields:
                message = f"Save to fields: {not_fields} are not fields of any step"
                issues.append(FlowIssue(message=message, node_id=node.id))
    for name, count in tool_names.items():
        if count > 1:
            issues.append(FlowIssue(message=f"Two tools are named '{name}'"))
    return issues


def _attached_anywhere(flow: Flow, tool_id: str) -> bool:
    """Attached tools get missing placeholders from the LLM's arguments."""
    return any(isinstance(node, StepNode) and tool_id in node.data.tools for node in flow.nodes)


def _check_reachable(flow: Flow, start_id: str, outgoing, nodes: dict) -> list[FlowIssue]:
    roots = [start_id] + [node.id for node in flow.nodes if node.type == GLOBAL_NODE]
    seen: set[str] = set()
    pending = list(roots)
    while pending:
        node_id = pending.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        pending += [edge.target for edge in outgoing[node_id]]
    attached = {
        tool_id for node in flow.nodes if node.type == STEP_NODE for tool_id in node.data.tools
    }
    return [
        FlowIssue(message="Nothing leads to this node", node_id=node.id)
        for node in flow.nodes
        if node.id not in seen and node.id not in attached and node.id in nodes
    ]

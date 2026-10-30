import type { Edge, Node } from "@xyflow/react";

import type {
  ApiFlowEdge,
  ApiFlowNode,
  Flow,
  FlowEdgeKind,
  FlowNodeData,
  FlowNodeType,
} from "@/lib/api";

export type CanvasNodeData = {
  nodeType: FlowNodeType;
  data: FlowNodeData;
  live: boolean;
  hasIssue: boolean;
  collected: string[];
};

export type CanvasEdgeData = { kind: FlowEdgeKind; condition: string };

export type CanvasNode = Node<CanvasNodeData, "flowNode">;
export type CanvasEdge = Edge<CanvasEdgeData>;

export const NODE_META: Record<
  FlowNodeType,
  { label: string; hint: string; icon: string; tint: string; border: string }
> = {
  start: {
    label: "Start",
    hint: "Where every call begins",
    icon: "▶",
    tint: "bg-emerald-50 text-emerald-600",
    border: "border-slate-200",
  },
  step: {
    label: "Step",
    hint: "Talks, collects fields",
    icon: "◆",
    tint: "bg-brand-50 text-brand-600",
    border: "border-slate-200",
  },
  tool: {
    label: "HTTP tool",
    hint: "Call any API",
    icon: "⇄",
    tint: "bg-sky-50 text-sky-600",
    border: "border-slate-200",
  },
  end: {
    label: "End",
    hint: "Finish with an outcome",
    icon: "■",
    tint: "bg-slate-100 text-slate-600",
    border: "border-slate-200",
  },
  transfer: {
    label: "Transfer",
    hint: "Hand to a person",
    icon: "☏",
    tint: "bg-red-50 text-red-600",
    border: "border-red-100",
  },
  global: {
    label: "Global",
    hint: "Fires from any step",
    icon: "✱",
    tint: "bg-red-50 text-red-600",
    border: "border-red-200",
  },
};

export const PALETTE: { group: string; types: FlowNodeType[] }[] = [
  { group: "Conversation", types: ["step"] },
  { group: "Actions", types: ["tool", "transfer"] },
  { group: "Flow", types: ["end", "global"] },
];

export const EDGE_KIND_LABELS: Record<FlowEdgeKind, string> = {
  condition: "When…",
  fields_complete: "All fields collected",
  success: "Tool succeeded",
  failure: "Tool failed",
  always: "Always",
};

export const ALLOWED_EDGE_KINDS: Record<FlowNodeType, FlowEdgeKind[]> = {
  start: ["always"],
  global: ["always"],
  step: ["condition", "fields_complete"],
  tool: ["success", "failure", "always"],
  end: [],
  transfer: [],
};

export function defaultData(type: FlowNodeType): FlowNodeData {
  switch (type) {
    case "step":
      return { name: "New step", instructions: "", fields: [], tools: [], use_knowledge: false };
    case "tool":
      return { name: "call_api", description: "", method: "GET", url: "https://", body: {} };
    case "end":
      return { outcome: "completed", message: "" };
    case "transfer":
      return { message: "", destination: "" };
    case "global":
      return { name: "Global", condition: "" };
    default:
      return {};
  }
}

export function nodeTitle(type: FlowNodeType, data: FlowNodeData): string {
  if (type === "step" || type === "global") return data.name || NODE_META[type].label;
  if (type === "tool") return data.name || "HTTP tool";
  if (type === "end") return data.outcome ? `Outcome: ${data.outcome}` : "End";
  if (type === "transfer") return data.message || "Transfer to a person";
  return "Start";
}

export function edgeLabel(kind: FlowEdgeKind, condition: string): string {
  return kind === "condition" ? condition || "When…?" : EDGE_KIND_LABELS[kind];
}

export function defaultEdgeKind(sourceType: FlowNodeType): FlowEdgeKind {
  return ALLOWED_EDGE_KINDS[sourceType][0] ?? "condition";
}

const EDGE_STYLE = { stroke: "#94a3b8", strokeWidth: 1.6 };
const FALLBACK_STYLE = { ...EDGE_STYLE, strokeDasharray: "5 4" };

export function edgeVisuals(kind: FlowEdgeKind, condition: string) {
  return {
    label: edgeLabel(kind, condition),
    style: kind === "failure" ? FALLBACK_STYLE : EDGE_STYLE,
    labelBgPadding: [6, 3] as [number, number],
    labelBgBorderRadius: 999,
    labelStyle: { fontSize: 10.5, fill: "#334155" },
    labelBgStyle: { fill: "#ffffff", stroke: "#e2e8f0" },
  };
}

export function toCanvas(flow: Flow): { nodes: CanvasNode[]; edges: CanvasEdge[] } {
  return {
    nodes: flow.nodes.map((node) => ({
      id: node.id,
      type: "flowNode",
      position: node.position,
      data: { nodeType: node.type, data: node.data, live: false, hasIssue: false, collected: [] },
    })),
    edges: flow.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      data: { kind: edge.kind, condition: edge.condition },
      ...edgeVisuals(edge.kind, edge.condition),
    })),
  };
}

export function toFlow(nodes: CanvasNode[], edges: CanvasEdge[]): Flow {
  return {
    nodes: nodes.map((node): ApiFlowNode => ({
      id: node.id,
      type: node.data.nodeType,
      position: { x: Math.round(node.position.x), y: Math.round(node.position.y) },
      data: node.data.data,
    })),
    edges: edges.map((edge): ApiFlowEdge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      kind: edge.data?.kind ?? "condition",
      condition: edge.data?.condition ?? "",
    })),
  };
}

export const STARTER_FLOW: Flow = {
  nodes: [
    { id: "start", type: "start", position: { x: 300, y: 0 }, data: {} },
    { id: "step_1", type: "step", position: { x: 300, y: 150 }, data: defaultData("step") },
  ],
  edges: [{ id: "start-step_1", source: "start", target: "step_1", kind: "always", condition: "" }],
};

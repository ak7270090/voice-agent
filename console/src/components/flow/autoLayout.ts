import ELK from "elkjs/lib/elk.bundled.js";

import type { CanvasEdge, CanvasNode } from "./flowModel";

const elk = new ELK();
const NODE_WIDTH = 240;
const NODE_HEIGHT = 90;
const LAYOUT_OPTIONS = {
  "elk.algorithm": "layered",
  "elk.direction": "DOWN",
  "elk.spacing.nodeNode": "50",
  "elk.layered.spacing.nodeNodeBetweenLayers": "70",
  "elk.edgeRouting": "SPLINES",
};

/** Lays the flow out top to bottom; global nodes and unattached tools stay where they are. */
export async function layoutFlow(nodes: CanvasNode[], edges: CanvasEdge[]): Promise<CanvasNode[]> {
  const connected = new Set(edges.flatMap((edge) => [edge.source, edge.target]));
  const placed = nodes.filter((node) => connected.has(node.id) && node.data.nodeType !== "global");
  const graph = await elk.layout({
    id: "flow",
    layoutOptions: LAYOUT_OPTIONS,
    children: placed.map((node) => ({
      id: node.id,
      width: node.measured?.width ?? NODE_WIDTH,
      height: node.measured?.height ?? NODE_HEIGHT,
    })),
    edges: edges
      .filter((edge) => placed.some((n) => n.id === edge.source))
      .map((edge) => ({ id: edge.id, sources: [edge.source], targets: [edge.target] })),
  });
  const positions = new Map(graph.children?.map((child) => [child.id, child]) ?? []);
  return nodes.map((node) => {
    const position = positions.get(node.id);
    return position ? { ...node, position: { x: position.x ?? 0, y: position.y ?? 0 } } : node;
  });
}

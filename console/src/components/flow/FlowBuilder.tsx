"use client";

import "@xyflow/react/dist/style.css";

import {
  addEdge,
  Background,
  BackgroundVariant,
  type Connection,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";
import clsx from "clsx";
import { AlertTriangle, LayoutGrid, Rocket, Save } from "lucide-react";
import Link from "next/link";
import { type DragEvent, useCallback, useMemo, useState } from "react";

import { TestCallPanel } from "@/components/test-call/TestCallPanel";
import { Button, Chip } from "@/components/ui/primitives";
import {
  type Agent,
  type FlowDraft,
  type FlowIssue,
  type FlowNodeData,
  type FlowNodeType,
  publishFlow,
  saveFlow,
} from "@/lib/api";

import { EdgePanel } from "./EdgePanel";
import { FlowNodeCard } from "./FlowNodeCard";
import {
  type CanvasEdge,
  type CanvasEdgeData,
  type CanvasNode,
  defaultData,
  defaultEdgeKind,
  edgeVisuals,
  STARTER_FLOW,
  toCanvas,
  toFlow,
} from "./flowModel";
import { NodePanel } from "./NodePanel";
import { DRAG_TYPE, NodePalette } from "./NodePalette";

const NODE_TYPES = { flowNode: FlowNodeCard };
type Tab = "test" | "settings" | "issues";

function withIssueMarks(nodes: CanvasNode[], issues: FlowIssue[]): CanvasNode[] {
  const flagged = new Set(issues.map((issue) => issue.node_id));
  return nodes.map((node) => ({ ...node, data: { ...node.data, hasIssue: flagged.has(node.id) } }));
}

function Builder({ agent, initial }: { agent: Agent; initial: FlowDraft }) {
  const canvas = useMemo(() => toCanvas(initial.flow ?? STARTER_FLOW), [initial.flow]);
  const [nodes, setNodes, onNodesChange] = useNodesState<CanvasNode>(
    withIssueMarks(canvas.nodes, initial.issues),
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState<CanvasEdge>(canvas.edges);
  const [issues, setIssues] = useState<FlowIssue[]>(initial.issues);
  const [publishedVersion, setPublishedVersion] = useState(initial.published_version);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("test");
  const [dirty, setDirty] = useState(initial.flow === null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const { screenToFlowPosition, fitView } = useReactFlow();

  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId) ?? null;
  const toolNodes = nodes.filter((node) => node.data.nodeType === "tool");
  const fieldNames = [
    ...new Set(nodes.flatMap((node) => (node.data.data.fields ?? []).map((field) => field.name))),
  ].filter(Boolean);

  const changed = useCallback(() => setDirty(true), []);

  function applyDraft(draft: FlowDraft) {
    setIssues(draft.issues);
    setPublishedVersion(draft.published_version);
    setNodes((current) => withIssueMarks(current, draft.issues));
    setDirty(false);
  }

  async function save(): Promise<FlowDraft | null> {
    setBusy(true);
    try {
      const draft = await saveFlow(agent.id, toFlow(nodes, edges));
      applyDraft(draft);
      setNotice(draft.issues.length ? `Saved with ${draft.issues.length} issues` : "Saved");
      if (draft.issues.length) setTab("issues");
      return draft;
    } catch (cause) {
      setNotice(`Could not save: ${(cause as Error).message}`);
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    const draft = await save();
    if (!draft || draft.issues.length) return;
    setBusy(true);
    try {
      const published = await publishFlow(agent.id);
      applyDraft(published);
      setNotice(`Published v${published.published_version}: phone calls now run this flow`);
    } catch (cause) {
      setNotice(`Could not publish: ${(cause as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function tidy() {
    // ELK is large, so it loads only when asked for.
    const { layoutFlow } = await import("./autoLayout");
    setNodes(await layoutFlow(nodes, edges));
    changed();
    window.requestAnimationFrame(() => fitView({ padding: 0.15 }));
  }

  function onConnect(connection: Connection) {
    const source = nodes.find((node) => node.id === connection.source);
    const kind = defaultEdgeKind(source?.data.nodeType ?? "step");
    const data: CanvasEdgeData = { kind, condition: "" };
    const id = `${connection.source}-${connection.target}-${Date.now().toString(36)}`;
    setEdges((current) => addEdge({ ...connection, id, data, ...edgeVisuals(kind, "") }, current));
    setSelectedEdgeId(id);
    setSelectedNodeId(null);
    setTab("settings");
    changed();
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    const type = event.dataTransfer.getData(DRAG_TYPE) as FlowNodeType;
    if (!type) return;
    const id = `${type}_${Date.now().toString(36)}`;
    const position = screenToFlowPosition({ x: event.clientX - 120, y: event.clientY - 30 });
    const node: CanvasNode = {
      id,
      type: "flowNode",
      position,
      data: {
        nodeType: type,
        data: defaultData(type),
        live: false,
        hasIssue: false,
        collected: [],
      },
    };
    setNodes((current) => [...current, node]);
    setSelectedNodeId(id);
    setSelectedEdgeId(null);
    setTab("settings");
    changed();
  }

  function updateNodeData(nodeId: string, data: FlowNodeData) {
    setNodes((current) =>
      current.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, data } } : node,
      ),
    );
    changed();
  }

  function updateEdgeData(edgeId: string, data: CanvasEdgeData) {
    setEdges((current) =>
      current.map((edge) =>
        edge.id === edgeId ? { ...edge, data, ...edgeVisuals(data.kind, data.condition) } : edge,
      ),
    );
    changed();
  }

  const showLiveNode = useCallback(
    (nodeId: string | null, fields: Record<string, unknown>) => {
      setNodes((current) =>
        current.map((node) => ({
          ...node,
          data: { ...node.data, live: node.id === nodeId, collected: Object.keys(fields) },
        })),
      );
    },
    [setNodes],
  );

  const sourceType = selectedEdge
    ? nodes.find((node) => node.id === selectedEdge.source)?.data.nodeType
    : undefined;

  return (
    <div className="flex h-screen flex-col">
      <header className="flex h-14 shrink-0 items-center gap-2.5 border-b border-slate-200 bg-white px-4 text-[13px]">
        <Link href={`/agents/${agent.id}`} className="text-slate-500 hover:text-slate-700">
          Agents / {agent.name}
        </Link>
        <span className="text-slate-300">/</span>
        <span className="font-semibold">Flow</span>
        {publishedVersion ? (
          <Chip tone="green">Published v{publishedVersion}</Chip>
        ) : (
          <Chip tone="amber">Not published</Chip>
        )}
        {dirty && <Chip>Unsaved changes</Chip>}
        {notice && <span className="text-xs text-slate-500">{notice}</span>}
        <div className="ml-auto flex items-center gap-2">
          <Button onClick={tidy}>
            <LayoutGrid size={14} /> Tidy up
          </Button>
          <Button onClick={save} disabled={busy}>
            <Save size={14} /> Save draft
          </Button>
          <Button variant="primary" onClick={publish} disabled={busy}>
            <Rocket size={14} /> Publish
          </Button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <NodePalette />
        <div className="relative flex-1" onDragOver={(e) => e.preventDefault()} onDrop={onDrop}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={NODE_TYPES}
            onNodesChange={(changes) => {
              onNodesChange(changes);
              if (changes.some((c) => c.type === "position" || c.type === "remove")) changed();
            }}
            onEdgesChange={(changes) => {
              onEdgesChange(changes);
              if (changes.some((c) => c.type === "remove")) changed();
            }}
            onConnect={onConnect}
            onNodeClick={(_, node) => {
              setSelectedNodeId(node.id);
              setSelectedEdgeId(null);
              setTab("settings");
            }}
            onEdgeClick={(_, edge) => {
              setSelectedEdgeId(edge.id);
              setSelectedNodeId(null);
              setTab("settings");
            }}
            onPaneClick={() => {
              setSelectedNodeId(null);
              setSelectedEdgeId(null);
            }}
            deleteKeyCode={["Backspace", "Delete"]}
            fitView
            fitViewOptions={{ padding: 0.15 }}
            proOptions={{ hideAttribution: true }}
            className="bg-[#fafbfd]"
          >
            <Background variant={BackgroundVariant.Dots} gap={18} color="#d9dee7" />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable nodeColor={(n) => (n.data?.live ? "#6366f1" : "#c7d2fe")} />
          </ReactFlow>
        </div>

        <aside className="flex w-[360px] shrink-0 flex-col border-l border-slate-200 bg-white">
          <div className="flex border-b border-slate-200 px-2 text-[13px]">
            {(["test", "settings", "issues"] as Tab[]).map((name) => (
              <button
                key={name}
                type="button"
                onClick={() => setTab(name)}
                className={clsx(
                  "-mb-px border-b-2 px-3 py-2.5",
                  tab === name
                    ? "border-brand-600 font-semibold text-brand-700"
                    : "border-transparent text-slate-500",
                )}
              >
                {name === "test" ? "Test call" : name === "settings" ? "Settings" : "Issues"}
                {name === "issues" && issues.length > 0 && (
                  <span className="ml-1.5 rounded-full bg-amber-100 px-1.5 text-[11px] text-amber-700">
                    {issues.length}
                  </span>
                )}
              </button>
            ))}
          </div>
          <div className={clsx("min-h-0 flex-1 overflow-y-auto", tab !== "test" && "hidden")}>
            {dirty && (
              <p className="m-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
                Test calls run the saved draft. Save to test your latest changes.
              </p>
            )}
            <div className="h-full p-3">
              <TestCallPanel
                agentId={agent.id}
                onCallEnded={() => undefined}
                onFlowNode={showLiveNode}
              />
            </div>
          </div>
          {tab === "settings" && (
            <div className="min-h-0 flex-1 overflow-y-auto">
              {selectedNode && (
                <NodePanel
                  key={selectedNode.id}
                  node={selectedNode}
                  toolNodes={toolNodes}
                  fieldNames={fieldNames}
                  onChange={(data) => updateNodeData(selectedNode.id, data)}
                  onDelete={() => {
                    setNodes((current) => current.filter((n) => n.id !== selectedNode.id));
                    setEdges((current) =>
                      current.filter(
                        (e) => e.source !== selectedNode.id && e.target !== selectedNode.id,
                      ),
                    );
                    setSelectedNodeId(null);
                    changed();
                  }}
                  onClose={() => setSelectedNodeId(null)}
                />
              )}
              {selectedEdge?.data && sourceType && (
                <EdgePanel
                  key={selectedEdge.id}
                  sourceType={sourceType}
                  data={selectedEdge.data}
                  onChange={(data) => updateEdgeData(selectedEdge.id, data)}
                  onDelete={() => {
                    setEdges((current) => current.filter((e) => e.id !== selectedEdge.id));
                    setSelectedEdgeId(null);
                    changed();
                  }}
                  onClose={() => setSelectedEdgeId(null)}
                />
              )}
              {!selectedNode && !selectedEdge && (
                <p className="p-4 text-[13px] text-slate-500">
                  Click a node or an edge to edit it. Drag from a node&apos;s bottom handle to
                  another node to connect them.
                </p>
              )}
            </div>
          )}
          {tab === "issues" && (
            <div className="min-h-0 flex-1 overflow-y-auto p-3">
              {issues.length === 0 && (
                <p className="p-1 text-[13px] text-slate-500">
                  No issues: the flow can be published.
                </p>
              )}
              {issues.map((issue, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => {
                    setSelectedNodeId(issue.node_id);
                    setSelectedEdgeId(issue.edge_id);
                    setTab("settings");
                  }}
                  className="mb-2 flex w-full items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-left text-xs text-amber-800"
                >
                  <AlertTriangle size={13} className="mt-px shrink-0" />
                  {issue.message}
                </button>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export function FlowBuilder(props: { agent: Agent; initial: FlowDraft }) {
  return (
    <ReactFlowProvider>
      <Builder {...props} />
    </ReactFlowProvider>
  );
}

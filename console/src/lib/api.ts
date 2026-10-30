export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type HealthReport = {
  status: "ok" | "degraded";
  dependencies: Record<string, string>;
};

export type VoiceSettings = {
  stt_model: string;
  tts_model: string;
  voice: string;
};

export type AgentFields = {
  name: string;
  description: string;
  instructions: string;
  greeting: string;
  llm_model: string;
  languages: string[];
  language_settings: Record<string, VoiceSettings>;
};

export type AgentStatus = "draft" | "live";

export type Agent = AgentFields & {
  id: string;
  template: string | null;
  status: AgentStatus;
  knowledge_base_ids: string[];
  has_flow: boolean;
  published_flow_version: number | null;
  created_at: string;
  updated_at: string;
};

export type AgentUpdate = Partial<AgentFields> & {
  status?: AgentStatus;
  knowledge_base_ids?: string[];
};

export type AgentTemplate = {
  id: string;
  name: string;
  summary: string;
  channel_label: string;
  fields: AgentFields;
};

export type BrowserCall = { url: string; token: string; room: string };

export type TranscriptTurn = { role: "user" | "assistant"; text: string };

export type Call = {
  id: string;
  agent_id: string;
  room_name: string;
  channel: string;
  status: "active" | "ended";
  started_at: string;
  ended_at: string | null;
  transcript: TranscriptTurn[];
  outcome: string | null;
  fields: Record<string, unknown>;
  flow_path: string[];
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : response.statusText;
    throw new ApiError(response.status, detail);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export async function fetchHealth(): Promise<HealthReport> {
  const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!response.ok && response.status !== 503) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }
  return response.json();
}

export const listTemplates = () => request<AgentTemplate[]>("/agent-templates");

export const listAgents = () => request<Agent[]>("/agents");

export const getAgent = (agentId: string) => request<Agent>(`/agents/${agentId}`);

export const createAgentFromTemplate = (templateId: string) =>
  request<Agent>("/agents/from-template", {
    method: "POST",
    body: JSON.stringify({ template_id: templateId }),
  });

export const updateAgent = (agentId: string, changes: AgentUpdate) =>
  request<Agent>(`/agents/${agentId}`, { method: "PATCH", body: JSON.stringify(changes) });

export const deleteAgent = (agentId: string) =>
  request<void>(`/agents/${agentId}`, { method: "DELETE" });

export const startBrowserCall = (agentId: string) =>
  request<BrowserCall>(`/agents/${agentId}/browser-calls`, { method: "POST" });

export const listCalls = (agentId: string) =>
  request<Call[]>(`/calls?agent_id=${encodeURIComponent(agentId)}`);

export type KnowledgeBase = {
  id: string;
  name: string;
  description: string;
  created_at: string;
  document_count: number;
  chunk_count: number;
};

export type DocumentStatus = "queued" | "processing" | "ready" | "failed";

export type KnowledgeDocument = {
  id: string;
  knowledge_base_id: string;
  name: string;
  source: "upload" | "url";
  content_type: string;
  size_bytes: number;
  source_url: string | null;
  status: DocumentStatus;
  error: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};

export type SearchHit = {
  document_id: string;
  document_name: string;
  text: string;
  score: number;
  similarity: number;
  keyword_overlap: number;
};

export type FlowNodeType = "start" | "step" | "tool" | "end" | "transfer" | "global";
export type FlowEdgeKind = "condition" | "fields_complete" | "success" | "failure" | "always";
export type FieldType = "text" | "name" | "number" | "date" | "time" | "yes_no" | "phone";

export type FieldSpec = {
  name: string;
  type: FieldType;
  description: string;
  required: boolean;
};

export type StepData = {
  name: string;
  instructions: string;
  fields: FieldSpec[];
  tools: string[];
  use_knowledge: boolean;
  say_on_enter: string;
};

export type ToolData = {
  name: string;
  description: string;
  method: "GET" | "POST";
  url: string;
  body: Record<string, string>;
  say_while_running: string;
  save_to_fields: Record<string, string>;
};

export type EndData = { outcome: string; message: string };
export type TransferData = { message: string; destination: string };
export type GlobalData = { name: string; condition: string };

export type FlowNodeData = Partial<StepData & ToolData & EndData & TransferData & GlobalData>;

export type ApiFlowNode = {
  id: string;
  type: FlowNodeType;
  position: { x: number; y: number };
  data: FlowNodeData;
};

export type ApiFlowEdge = {
  id: string;
  source: string;
  target: string;
  kind: FlowEdgeKind;
  condition: string;
};

export type Flow = { nodes: ApiFlowNode[]; edges: ApiFlowEdge[] };

export type FlowIssue = { message: string; node_id: string | null; edge_id: string | null };

export type FlowDraft = {
  flow: Flow | null;
  issues: FlowIssue[];
  published_version: number | null;
};

export type FlowVersion = { version: number; published_at: string; node_count: number };

export const getFlow = (agentId: string) => request<FlowDraft>(`/agents/${agentId}/flow`);

export const saveFlow = (agentId: string, flow: Flow) =>
  request<FlowDraft>(`/agents/${agentId}/flow`, { method: "PUT", body: JSON.stringify(flow) });

export const publishFlow = (agentId: string) =>
  request<FlowDraft>(`/agents/${agentId}/flow/publish`, { method: "POST" });

export const listFlowVersions = (agentId: string) =>
  request<FlowVersion[]>(`/agents/${agentId}/flow/versions`);

export const listKnowledgeBases = () => request<KnowledgeBase[]>("/knowledge-bases");

export const createKnowledgeBase = (name: string) =>
  request<KnowledgeBase>("/knowledge-bases", { method: "POST", body: JSON.stringify({ name }) });

export const deleteKnowledgeBase = (knowledgeBaseId: string) =>
  request<void>(`/knowledge-bases/${knowledgeBaseId}`, { method: "DELETE" });

export const listDocuments = (knowledgeBaseId: string) =>
  request<KnowledgeDocument[]>(`/knowledge-bases/${knowledgeBaseId}/documents`);

export async function uploadDocument(knowledgeBaseId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  // No JSON content type: the browser sets the multipart boundary itself.
  const response = await fetch(`${API_URL}/knowledge-bases/${knowledgeBaseId}/documents`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  return (await response.json()) as KnowledgeDocument;
}

export const addUrlDocument = (knowledgeBaseId: string, url: string) =>
  request<KnowledgeDocument>(`/knowledge-bases/${knowledgeBaseId}/documents/from-url`, {
    method: "POST",
    body: JSON.stringify({ url }),
  });

export const deleteDocument = (knowledgeBaseId: string, documentId: string) =>
  request<void>(`/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`, {
    method: "DELETE",
  });

export const searchKnowledgeBase = (knowledgeBaseId: string, query: string) =>
  request<SearchHit[]>(`/knowledge-bases/${knowledgeBaseId}/search`, {
    method: "POST",
    body: JSON.stringify({ query }),
  });

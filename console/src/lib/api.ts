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
  voicemail_message: string;
  llm_model: string;
  languages: string[];
  language_settings: Record<string, VoiceSettings>;
  analysis_fields: AnalysisField[];
  success_rule: string;
};

export type AnalysisFieldType = "text" | "choice" | "yes_no" | "number";

export type AnalysisField = {
  name: string;
  type: AnalysisFieldType;
  description: string;
  choices: string[];
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

export type TranscriptTurn = { role: "user" | "assistant"; text: string; at: number | null };

export type ToolCall = {
  name: string;
  by: "flow" | "llm";
  at: number;
  ms: number;
  ok: boolean;
  unavailable: boolean;
  result: string;
};

export type CallCost = {
  llm: number;
  stt: number;
  tts: number;
  phone: number;
  analysis: number;
  total: number;
  llm_unpriced: boolean;
};

export type CallAnalysis = {
  summary: string;
  successful: boolean;
  success_reason: string;
  sentiment: "positive" | "neutral" | "negative";
  fields: Record<string, string | number | boolean | null>;
  qa_score: number;
  qa_notes: string;
};

export type Call = {
  id: string;
  agent_id: string;
  room_name: string;
  channel: string;
  direction: "inbound" | "outbound";
  remote_number: string | null;
  campaign_contact_id: string | null;
  status: "active" | "ended";
  started_at: string;
  ended_at: string | null;
  transcript: TranscriptTurn[];
  outcome: string | null;
  fields: Record<string, unknown>;
  flow_path: string[];
  turn_latency_ms: Record<string, number>[];
  interruptions: number;
  usage: Record<string, number>;
  cost: Partial<CallCost>;
  tool_calls: ToolCall[];
  analysis_status: "pending" | "done" | "skipped" | "failed" | null;
  analysis: Partial<CallAnalysis>;
  langfuse_url: string | null;
  recording_url: string | null;
};

export type CallFilters = {
  agent_id?: string;
  channel?: string;
  direction?: string;
  outcome?: string;
};

export type Metrics = {
  days: { day: string; calls: number }[];
  calls: number;
  outcomes: Record<string, number>;
  average_cost: number | null;
  total_cost: number;
  average_duration_seconds: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  agents: { agent_id: string; name: string; calls: number; analysed: number; successful: number }[];
};

export const listAllCalls = (filters: CallFilters) => {
  const query = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value) as [string, string][],
  );
  return request<Call[]>(`/calls?${query}`);
};

export const getCall = (callId: string) => request<Call>(`/calls/${callId}`);

export const getMetrics = (days: number) => request<Metrics>(`/metrics?days=${days}`);

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

export type PhoneProvider = "livekit" | "sip_trunk";

export type PhoneNumber = {
  id: string;
  number: string;
  label: string;
  provider: PhoneProvider;
  agent_id: string | null;
  dispatch_rule_id: string;
  can_call_out: boolean;
  can_transfer: boolean;
  created_at: string;
};

export type OutboundTrunk = { address: string; username: string; password: string };

export type PhoneNumberCreate = {
  number: string;
  label: string;
  provider: PhoneProvider;
  agent_id: string | null;
  outbound: OutboundTrunk | null;
};

export const listPhoneNumbers = () => request<PhoneNumber[]>("/phone-numbers");

export const addPhoneNumber = (body: PhoneNumberCreate) =>
  request<PhoneNumber>("/phone-numbers", { method: "POST", body: JSON.stringify(body) });

export const updatePhoneNumber = (
  numberId: string,
  changes: { label?: string; agent_id?: string | null },
) =>
  request<PhoneNumber>(`/phone-numbers/${numberId}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });

export const deletePhoneNumber = (numberId: string) =>
  request<void>(`/phone-numbers/${numberId}`, { method: "DELETE" });

export const startPhoneCall = (agentId: string, toNumber: string, fromNumberId: string) =>
  request<{ room: string }>(`/agents/${agentId}/phone-calls`, {
    method: "POST",
    body: JSON.stringify({ to_number: toNumber, from_number_id: fromNumberId }),
  });

export type CampaignStatus = "draft" | "running" | "paused" | "completed";
export type ContactStatus =
  "pending" | "calling" | "retry" | "done" | "failed" | "skipped" | "opted_out";

export type CampaignSettings = {
  name: string;
  agent_id: string;
  from_number_id: string;
  window_start: string;
  window_end: string;
  timezone: string;
  max_concurrent: number;
  max_attempts: number;
  retry_after_minutes: number;
};

export type Campaign = CampaignSettings & {
  id: string;
  status: CampaignStatus;
  created_at: string;
  counts: Partial<Record<ContactStatus, number>>;
};

export type CampaignContact = {
  id: string;
  phone: string;
  name: string;
  variables: Record<string, string>;
  consent: boolean;
  status: ContactStatus;
  attempts: number;
  next_attempt_at: string | null;
  outcome: string | null;
  updated_at: string;
};

export type ContactImport = {
  added: number;
  skipped: number;
  rejected: { row: number; reason: string }[];
};

export const listCampaigns = () => request<Campaign[]>("/campaigns");

export const getCampaign = (campaignId: string) => request<Campaign>(`/campaigns/${campaignId}`);

export const createCampaign = (settings: CampaignSettings) =>
  request<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(settings) });

export const startCampaign = (campaignId: string) =>
  request<Campaign>(`/campaigns/${campaignId}/start`, { method: "POST" });

export const pauseCampaign = (campaignId: string) =>
  request<Campaign>(`/campaigns/${campaignId}/pause`, { method: "POST" });

export const listCampaignContacts = (campaignId: string) =>
  request<CampaignContact[]>(`/campaigns/${campaignId}/contacts`);

export async function importContacts(campaignId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  // No JSON content type: the browser sets the multipart boundary itself.
  const response = await fetch(`${API_URL}/campaigns/${campaignId}/contacts/csv`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  return (await response.json()) as ContactImport;
}

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
  wait_after_enter: boolean;
};

export type ToolData = {
  name: string;
  description: string;
  method: "GET" | "POST";
  url: string;
  body: Record<string, string>;
  say_while_running: string;
  save_to_fields: Record<string, string>;
  result_fields: string[];
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

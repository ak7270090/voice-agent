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
  created_at: string;
  updated_at: string;
};

export type AgentUpdate = Partial<AgentFields> & { status?: AgentStatus };

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

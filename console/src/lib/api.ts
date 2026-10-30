export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type HealthReport = {
  status: "ok" | "degraded";
  dependencies: Record<string, string>;
};

export async function fetchHealth(): Promise<HealthReport> {
  const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!response.ok && response.status !== 503) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }
  return response.json();
}

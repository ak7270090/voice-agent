import type { Call } from "@/lib/api";

// Dollars: calls cost fractions of a cent, so small amounts keep four decimals.
export function formatCost(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value >= 1 ? `$${value.toFixed(2)}` : `$${value.toFixed(4)}`;
}

export function formatSeconds(totalSeconds: number | null | undefined): string {
  if (totalSeconds === null || totalSeconds === undefined) return "—";
  const seconds = Math.round(totalSeconds);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function callSeconds(call: Call): number | null {
  if (!call.ended_at) return null;
  return (new Date(call.ended_at).getTime() - new Date(call.started_at).getTime()) / 1000;
}

// Seconds into the call, from a Unix time (transcript lines and tool calls).
export function offsetFromStart(call: Call, at: number | null): string {
  if (at === null) return "";
  return formatSeconds(Math.max(0, at - new Date(call.started_at).getTime() / 1000));
}

export function channelLabel(call: Call): string {
  if (call.channel !== "phone") return call.channel;
  const arrow = call.direction === "outbound" ? "to" : "from";
  return call.remote_number ? `phone ${arrow} ${call.remote_number}` : "phone";
}

/** An outcome as people read it: "reschedule_requested" → "Reschedule requested". */
export function outcomeLabel(outcome: string): string {
  const words = outcome.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

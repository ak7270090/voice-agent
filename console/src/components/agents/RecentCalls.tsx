import { Card, Chip } from "@/components/ui/primitives";
import type { Call } from "@/lib/api";

function duration(call: Call): string {
  if (!call.ended_at) return "—";
  const seconds = Math.round(
    (new Date(call.ended_at).getTime() - new Date(call.started_at).getTime()) / 1000,
  );
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function RecentCalls({ calls }: { calls: Call[] }) {
  return (
    <Card>
      <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
        <h3 className="text-[13px] font-semibold">Recent test calls</h3>
        <Chip>{calls.length}</Chip>
      </div>
      {calls.length === 0 ? (
        <p className="px-4 py-3 text-[13px] text-slate-400">No calls yet.</p>
      ) : (
        <table className="w-full text-[13px]">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="px-4 py-2 font-medium">Started</th>
              <th className="px-4 py-2 font-medium">Channel</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Outcome</th>
              <th className="px-4 py-2 text-right font-medium">Turns</th>
              <th className="px-4 py-2 text-right font-medium">Duration</th>
            </tr>
          </thead>
          <tbody>
            {calls.map((call) => (
              <tr key={call.id} className="border-t border-slate-100 text-slate-700">
                <td className="px-4 py-2">{new Date(call.started_at).toLocaleString()}</td>
                <td className="px-4 py-2">{call.channel}</td>
                <td className="px-4 py-2">
                  <Chip tone={call.status === "active" ? "green" : "neutral"}>{call.status}</Chip>
                </td>
                <td className="px-4 py-2">
                  {call.outcome ? <Chip tone="brand">{call.outcome}</Chip> : "—"}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">{call.transcript.length}</td>
                <td className="px-4 py-2 text-right tabular-nums">{duration(call)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

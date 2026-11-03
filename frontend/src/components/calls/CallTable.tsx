import Link from "next/link";

import {
  callSeconds,
  channelLabel,
  formatCost,
  formatSeconds,
  outcomeLabel,
} from "@/components/calls/format";
import { Chip } from "@/components/ui/primitives";
import type { Call } from "@/lib/api";
import { dashboardPath } from "@/lib/paths";

export function SuccessChip({ call }: { call: Call }) {
  if (call.analysis_status === "pending") return <Chip>analysing…</Chip>;
  if (call.analysis_status !== "done") return <span className="text-slate-400">—</span>;
  return call.analysis.successful ? (
    <Chip tone="green">successful</Chip>
  ) : (
    <Chip tone="red">not successful</Chip>
  );
}

export function CallTable({
  calls,
  agentNames = {},
}: {
  calls: Call[];
  agentNames?: Record<string, string>;
}) {
  if (calls.length === 0) {
    return <p className="px-4 py-3 text-[13px] text-slate-400">No calls yet.</p>;
  }
  const showAgent = Object.keys(agentNames).length > 0;
  return (
    <table className="w-full text-[13px]">
      <thead>
        <tr className="text-left text-xs text-slate-500">
          <th className="px-4 py-2 font-medium">Started</th>
          {showAgent && <th className="px-4 py-2 font-medium">Agent</th>}
          <th className="px-4 py-2 font-medium">Channel</th>
          <th className="px-4 py-2 font-medium">Outcome</th>
          <th className="px-4 py-2 font-medium">Analysis</th>
          <th className="px-4 py-2 text-right font-medium">Turns</th>
          <th className="px-4 py-2 text-right font-medium">Duration</th>
          <th className="px-4 py-2 text-right font-medium">Cost</th>
        </tr>
      </thead>
      <tbody>
        {calls.map((call) => (
          <tr key={call.id} className="border-t border-slate-100 text-slate-700 hover:bg-slate-50">
            <td className="px-4 py-2">
              <Link
                href={dashboardPath(`/calls/${call.id}`)}
                className="text-brand-600 hover:underline"
              >
                {new Date(call.started_at).toLocaleString()}
              </Link>
            </td>
            {showAgent && (
              <td className="px-4 py-2">{agentNames[call.agent_id] ?? "Deleted agent"}</td>
            )}
            <td className="px-4 py-2">{channelLabel(call)}</td>
            <td className="px-4 py-2">
              {call.status === "active" ? (
                <Chip tone="green" dot>
                  live
                </Chip>
              ) : call.outcome ? (
                <Chip tone="brand">{outcomeLabel(call.outcome)}</Chip>
              ) : (
                "—"
              )}
            </td>
            <td className="px-4 py-2">
              <SuccessChip call={call} />
            </td>
            <td className="px-4 py-2 text-right tabular-nums">{call.transcript.length}</td>
            <td className="px-4 py-2 text-right tabular-nums">
              {formatSeconds(callSeconds(call))}
            </td>
            <td className="px-4 py-2 text-right tabular-nums">{formatCost(call.cost.total)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

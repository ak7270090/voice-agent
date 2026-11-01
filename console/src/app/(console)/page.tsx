"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { formatCost, formatSeconds } from "@/components/calls/format";
import { DailyBars, OutcomeBars, StatTile } from "@/components/dashboard/Charts";
import { ServiceStatus } from "@/components/shell/ServiceStatus";
import { Card, PageHeader } from "@/components/ui/primitives";
import { getMetrics, type Metrics } from "@/lib/api";

const PERIODS = [7, 14, 30];
// The busiest agents; the Calls page filters by any agent.
const AGENT_ROWS = 8;

function seconds(ms: number | null): string {
  return ms === null ? "—" : `${(ms / 1000).toFixed(2)} s`;
}

export default function OverviewPage() {
  const [days, setDays] = useState(14);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMetrics(days)
      .then(setMetrics)
      .catch((cause: Error) => setError(cause.message));
  }, [days]);

  return (
    <>
      <PageHeader>
        <span className="font-semibold">Overview</span>
        <span className="ml-auto flex rounded-lg border border-slate-200 bg-white p-0.5">
          {PERIODS.map((period) => (
            <button
              key={period}
              onClick={() => setDays(period)}
              className={`rounded-md px-2.5 py-1 text-xs ${days === period ? "bg-slate-100 font-semibold text-slate-900" : "text-slate-500"}`}
            >
              {period} days
            </button>
          ))}
        </span>
      </PageHeader>
      <div className="flex flex-col gap-4 p-6">
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}
        {metrics && (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
              <StatTile label="Calls" value={String(metrics.calls)} />
              <StatTile
                label="Average cost"
                value={formatCost(metrics.average_cost)}
                note={`${formatCost(metrics.total_cost)} in total`}
              />
              <StatTile
                label="Average length"
                value={formatSeconds(metrics.average_duration_seconds)}
              />
              <StatTile
                label="Reply delay, typical"
                value={seconds(metrics.latency_p50_ms)}
                note="p50, caller stops → agent speaks"
              />
              <StatTile
                label="Reply delay, slow"
                value={seconds(metrics.latency_p95_ms)}
                note="p95: 1 reply in 20 is slower"
              />
            </div>
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <Card className="flex flex-col gap-3 p-4">
                <h2 className="text-[13px] font-semibold">Calls per day</h2>
                <DailyBars days={metrics.days} />
              </Card>
              <Card className="flex flex-col gap-3 p-4">
                <h2 className="text-[13px] font-semibold">Outcomes</h2>
                <OutcomeBars outcomes={metrics.outcomes} />
              </Card>
            </div>
            <Card>
              <h2 className="border-b border-slate-100 px-4 py-3 text-[13px] font-semibold">
                Success by agent
              </h2>
              {metrics.agents.length === 0 ? (
                <p className="px-4 py-3 text-[13px] text-slate-400">No calls in this period.</p>
              ) : (
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="text-left text-xs text-slate-500">
                      <th className="px-4 py-2 font-medium">Agent</th>
                      <th className="px-4 py-2 text-right font-medium">Calls</th>
                      <th className="px-4 py-2 text-right font-medium">Analysed</th>
                      <th className="px-4 py-2 text-right font-medium">Successful</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.agents.slice(0, AGENT_ROWS).map((row) => (
                      <tr key={row.agent_id} className="border-t border-slate-100">
                        <td className="px-4 py-2">
                          <Link
                            href={`/calls?agent_id=${row.agent_id}`}
                            className="text-brand-600 hover:underline"
                          >
                            {row.name}
                          </Link>
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">{row.calls}</td>
                        <td className="px-4 py-2 text-right tabular-nums">{row.analysed}</td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {row.analysed
                            ? `${row.successful} (${Math.round((row.successful / row.analysed) * 100)}%)`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </>
        )}
        <div className="max-w-md">
          <ServiceStatus />
        </div>
      </div>
    </>
  );
}

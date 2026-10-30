"use client";

import clsx from "clsx";
import { useEffect, useState } from "react";

import { fetchHealth, type HealthReport } from "@/lib/api";

const REFRESH_INTERVAL_MS = 10_000;
const HEALTHY = "ok";
const SERVICE_LABELS: Record<string, string> = { api: "API" };

export function ServiceStatus() {
  const [report, setReport] = useState<HealthReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () =>
      fetchHealth()
        .then((latest) => {
          setReport(latest);
          setError(null);
        })
        .catch(() => setError("API not reachable"));
    refresh();
    const timer = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

  const rows: [string, string][] = error
    ? [["api", error]]
    : [["api", HEALTHY], ...Object.entries(report?.dependencies ?? {})];

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center border-b border-slate-100 px-4 py-3.5">
        <h3 className="text-[13px] font-semibold">Services</h3>
        <span className="ml-2 text-[13px] text-slate-500">refreshes every 10 s</span>
      </div>
      <ul className="divide-y divide-slate-100">
        {rows.map(([name, state]) => (
          <li key={name} className="flex items-center px-4 py-2.5 text-[13px]">
            <span className="capitalize text-slate-700">{SERVICE_LABELS[name] ?? name}</span>
            <span
              className={clsx(
                "ml-auto inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium",
                state === HEALTHY ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600",
              )}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-current" />
              {state}
            </span>
          </li>
        ))}
        {!report && !error && <li className="px-4 py-2.5 text-[13px] text-slate-400">Checking…</li>}
      </ul>
    </div>
  );
}

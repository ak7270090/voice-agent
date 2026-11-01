"use client";

import { useState } from "react";

import { Card } from "@/components/ui/primitives";

// One series per chart, so one hue: the console's brand colour.
const BAR = "bg-brand-500";
const BAR_HOVER = "bg-brand-700";

export function StatTile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <Card className="flex flex-col gap-1 p-4">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-2xl font-semibold tabular-nums tracking-tight text-slate-900">
        {value}
      </span>
      {note && <span className="text-[11px] text-slate-400">{note}</span>}
    </Card>
  );
}

/** Calls per day: one column per day from the baseline, a tooltip on hover. */
export function DailyBars({ days }: { days: { day: string; calls: number }[] }) {
  const [hovered, setHovered] = useState<number | null>(null);
  const most = Math.max(1, ...days.map((entry) => entry.calls));
  const label = (day: string) =>
    new Date(`${day}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  return (
    <div className="relative">
      <div className="flex h-40 items-end gap-[2px] border-b border-slate-200">
        {days.map((entry, index) => (
          <div
            key={entry.day}
            className="flex h-full flex-1 items-end"
            onMouseEnter={() => setHovered(index)}
            onMouseLeave={() => setHovered(null)}
          >
            <div
              className={`w-full rounded-t ${hovered === index ? BAR_HOVER : BAR}`}
              style={{ height: entry.calls ? `${(entry.calls / most) * 100}%` : 0 }}
            />
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-slate-400">
        <span>{days.length ? label(days[0].day) : ""}</span>
        <span>{days.length ? label(days[days.length - 1].day) : ""}</span>
      </div>
      {hovered !== null && (
        <div
          className="pointer-events-none absolute -top-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs shadow-sm"
          style={{
            left: `${((hovered + 0.5) / days.length) * 100}%`,
            transform: "translateX(-50%)",
          }}
        >
          <span className="text-slate-500">{label(days[hovered].day)}</span>{" "}
          <span className="font-semibold tabular-nums text-slate-900">
            {days[hovered].calls} calls
          </span>
        </div>
      )}
    </div>
  );
}

/** Outcome mix: one row per outcome, longest first, its count and share beside it. */
export function OutcomeBars({ outcomes }: { outcomes: Record<string, number> }) {
  const rows = Object.entries(outcomes).sort(([, a], [, b]) => b - a);
  const total = rows.reduce((sum, [, count]) => sum + count, 0);
  if (total === 0) return <p className="text-[13px] text-slate-400">No calls in this period.</p>;
  const most = rows[0][1];
  return (
    <ul className="flex flex-col gap-2">
      {rows.map(([outcome, count]) => (
        <li
          key={outcome}
          className="grid grid-cols-[9rem_1fr_5rem] items-center gap-3 text-xs"
          title={`${outcome}: ${count} of ${total} calls`}
        >
          <span className="truncate text-slate-600">{outcome}</span>
          <span className="h-3 rounded-r bg-slate-100">
            <span
              className={`block h-3 rounded-r ${BAR}`}
              style={{ width: `${(count / most) * 100}%` }}
            />
          </span>
          <span className="text-right tabular-nums text-slate-700">
            {count} · {Math.round((count / total) * 100)}%
          </span>
        </li>
      ))}
    </ul>
  );
}

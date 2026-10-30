import type { ReactNode } from "react";

export const INPUT =
  "w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-[13px] outline-none focus:border-brand-500";

export function Labelled({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      {children}
      {hint && <span className="text-[11px] text-slate-400">{hint}</span>}
    </label>
  );
}

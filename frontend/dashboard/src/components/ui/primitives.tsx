import clsx from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { TIME_ZONE_CHOICES } from "@/lib/constants";

const CHIP_TONES = {
  neutral: "bg-slate-100 text-slate-700",
  brand: "bg-brand-50 text-brand-700",
  green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700",
  red: "bg-red-50 text-red-600",
};

export function Chip({
  children,
  tone = "neutral",
  dot = false,
}: {
  children: ReactNode;
  tone?: keyof typeof CHIP_TONES;
  dot?: boolean;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-medium",
        CHIP_TONES[tone],
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export function Button({
  variant = "secondary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }) {
  return (
    <button
      className={clsx(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border px-3 py-1.5 text-[13px] font-medium disabled:opacity-50",
        variant === "primary" && "border-brand-600 bg-brand-600 text-white hover:bg-brand-700",
        variant === "secondary" && "border-slate-200 bg-white text-slate-700 hover:bg-slate-50",
        variant === "danger" && "border-red-200 bg-white text-red-600 hover:bg-red-50",
        className,
      )}
      {...props}
    />
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={clsx("rounded-xl border border-slate-200 bg-white", className)}>{children}</div>
  );
}

export function PageHeader({ children }: { children: ReactNode }) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-6 text-[13px]">
      {children}
    </header>
  );
}

/** A list of common zones; a zone saved earlier that is not in it stays selectable. */
export function TimeZoneSelect({
  value,
  className,
  onChange,
}: {
  value: string;
  className: string;
  onChange: (zone: string) => void;
}) {
  const known = TIME_ZONE_CHOICES.some((choice) => choice.value === value);
  return (
    <select className={className} value={value} onChange={(e) => onChange(e.target.value)}>
      {!known && value && <option value={value}>{value}</option>}
      {TIME_ZONE_CHOICES.map((choice) => (
        <option key={choice.value} value={choice.value}>
          {choice.label}
        </option>
      ))}
    </select>
  );
}

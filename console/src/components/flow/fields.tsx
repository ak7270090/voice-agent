"use client";

import { Plus } from "lucide-react";
import { type ReactNode, useState } from "react";

export const INPUT =
  "w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-[13px] outline-none focus:border-brand-500";

/** A comma-separated list, kept as typed until the input loses focus. */
export function ListInput({
  values,
  placeholder,
  onChange,
}: {
  values: string[];
  placeholder: string;
  onChange: (values: string[]) => void;
}) {
  const [text, setText] = useState(values.join(", "));
  return (
    <input
      className={`${INPUT} font-mono text-xs`}
      value={text}
      placeholder={placeholder}
      onChange={(e) => setText(e.target.value)}
      onBlur={() =>
        onChange(
          text
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean),
        )
      }
    />
  );
}

export function KeyValueEditor({
  label,
  rows,
  keyPlaceholder = "",
  valuePlaceholder = "",
  onChange,
}: {
  label: string;
  rows: Record<string, string>;
  keyPlaceholder?: string;
  valuePlaceholder?: string;
  onChange: (b: Record<string, string>) => void;
}) {
  const entries = Object.entries(rows);
  const rebuild = (rows: [string, string][]) => onChange(Object.fromEntries(rows));
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      {entries.map(([key, value], index) => (
        <div key={index} className="flex gap-1.5">
          <input
            className={`${INPUT} font-mono text-xs`}
            value={key}
            placeholder={keyPlaceholder}
            onChange={(e) =>
              rebuild(entries.map((entry, i) => (i === index ? [e.target.value, entry[1]] : entry)))
            }
          />
          <input
            className={`${INPUT} font-mono text-xs`}
            value={value}
            placeholder={valuePlaceholder}
            onChange={(e) =>
              rebuild(entries.map((entry, i) => (i === index ? [entry[0], e.target.value] : entry)))
            }
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => rebuild([...entries, [`key_${entries.length + 1}`, ""]])}
        className="flex items-center gap-1 self-start text-xs font-medium text-brand-700"
      >
        <Plus size={13} /> Add key
      </button>
    </div>
  );
}

/** JSON edited as text; applied when it parses, otherwise the error is shown. */
export function JsonEditor({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}) {
  const [text, setText] = useState(JSON.stringify(value, null, 2));
  const [error, setError] = useState<string | null>(null);
  return (
    <Labelled label={label} hint={error ?? hint}>
      <textarea
        className={`${INPUT} min-h-[120px] font-mono text-xs leading-relaxed ${error ? "border-red-300" : ""}`}
        value={text}
        spellCheck={false}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => {
          try {
            const parsed = JSON.parse(text || "{}");
            if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
              throw new Error("the body must be a JSON object");
            }
            setError(null);
            onChange(parsed);
          } catch (cause) {
            setError(`Not saved: ${(cause as Error).message}`);
          }
        }}
      />
    </Labelled>
  );
}

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

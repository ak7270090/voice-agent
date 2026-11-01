"use client";

import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/primitives";
import type { AnalysisField, AnalysisFieldType } from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-[13px] outline-none focus:border-brand-500";
const TYPES: { value: AnalysisFieldType; label: string }[] = [
  { value: "text", label: "Text" },
  { value: "choice", label: "Choice" },
  { value: "yes_no", label: "Yes / no" },
  { value: "number", label: "Number" },
];

/** What the post-call analysis reports for every call of this agent. */
export function AnalysisSettings({
  fields,
  successRule,
  onFieldsChange,
  onSuccessRuleChange,
}: {
  fields: AnalysisField[];
  successRule: string;
  onFieldsChange: (fields: AnalysisField[]) => void;
  onSuccessRuleChange: (rule: string) => void;
}) {
  const update = (index: number, changes: Partial<AnalysisField>) =>
    onFieldsChange(fields.map((field, n) => (n === index ? { ...field, ...changes } : field)));

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-200 p-3">
      <div>
        <h3 className="text-xs font-semibold text-slate-700">Post-call analysis</h3>
        <p className="text-[11px] text-slate-400">
          After each call: a summary, sentiment, a QA score, whether it succeeded, and these fields.
        </p>
      </div>
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-slate-600">A call is successful when</span>
        <input
          className={INPUT}
          value={successRule}
          placeholder="e.g. An appointment was booked"
          onChange={(e) => onSuccessRuleChange(e.target.value)}
        />
      </label>
      {fields.map((field, index) => (
        <div key={index} className="grid grid-cols-[10rem_7rem_1fr_auto] items-start gap-2">
          <input
            className={INPUT}
            value={field.name}
            placeholder="field_name"
            onChange={(e) => update(index, { name: e.target.value })}
          />
          <select
            className={INPUT}
            value={field.type}
            onChange={(e) => {
              const type = e.target.value as AnalysisFieldType;
              update(index, { type, choices: type === "choice" ? field.choices : [] });
            }}
          >
            {TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <div className="flex flex-col gap-1.5">
            <input
              className={INPUT}
              value={field.description}
              placeholder="The question, e.g. Did the caller ask about fees?"
              onChange={(e) => update(index, { description: e.target.value })}
            />
            {field.type === "choice" && (
              <input
                className={INPUT}
                defaultValue={field.choices.join(", ")}
                placeholder="Choices, comma-separated"
                onBlur={(e) =>
                  update(index, {
                    choices: e.target.value
                      .split(",")
                      .map((choice) => choice.trim())
                      .filter(Boolean),
                  })
                }
              />
            )}
          </div>
          <Button
            type="button"
            variant="danger"
            aria-label={`Remove ${field.name || "field"}`}
            onClick={() => onFieldsChange(fields.filter((_, n) => n !== index))}
          >
            <Trash2 size={14} />
          </Button>
        </div>
      ))}
      <div>
        <Button
          type="button"
          onClick={() =>
            onFieldsChange([...fields, { name: "", type: "text", description: "", choices: [] }])
          }
        >
          <Plus size={14} /> Add field
        </Button>
      </div>
    </div>
  );
}

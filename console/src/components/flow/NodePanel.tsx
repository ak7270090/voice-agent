"use client";

import { Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

import type { FieldSpec, FieldType, FlowNodeData } from "@/lib/api";

import { INPUT, Labelled } from "./fields";
import { type CanvasNode, NODE_META } from "./flowModel";

const FIELD_TYPES: FieldType[] = ["text", "name", "number", "date", "time", "yes_no", "phone"];

type Props = {
  node: CanvasNode;
  toolNodes: CanvasNode[];
  onChange: (data: FlowNodeData) => void;
  onDelete: () => void;
  onClose: () => void;
};

export function NodePanel({ node, toolNodes, onChange, onDelete, onClose }: Props) {
  const { nodeType, data } = node.data;
  const set = (changes: Partial<FlowNodeData>) => onChange({ ...data, ...changes });

  return (
    <div className="flex flex-col gap-3.5 p-4">
      <div className="flex items-center gap-2">
        <h3 className="text-[13px] font-semibold">{NODE_META[nodeType].label} settings</h3>
        <button
          type="button"
          onClick={onClose}
          className="ml-auto text-slate-400"
          aria-label="Close"
        >
          <X size={16} />
        </button>
      </div>

      {nodeType === "start" && (
        <p className="text-[13px] text-slate-500">
          Every call begins here, after the agent&apos;s greeting. Connect it to the first step.
        </p>
      )}

      {(nodeType === "step" || nodeType === "global") && (
        <Labelled label="Name">
          <input
            className={INPUT}
            value={data.name ?? ""}
            onChange={(e) => set({ name: e.target.value })}
          />
        </Labelled>
      )}

      {nodeType === "step" && (
        <>
          <Labelled label="What the agent does here" hint="Added to the agent's own instructions">
            <textarea
              className={`${INPUT} min-h-[110px] text-xs leading-relaxed`}
              value={data.instructions ?? ""}
              onChange={(e) => set({ instructions: e.target.value })}
            />
          </Labelled>
          <Labelled
            label="Say on entering (optional)"
            hint="Spoken the moment the call arrives here; {field} placeholders are filled in"
          >
            <input
              className={INPUT}
              value={data.say_on_enter ?? ""}
              placeholder="e.g. Sure, I can help with that."
              onChange={(e) => set({ say_on_enter: e.target.value })}
            />
          </Labelled>
          <label className="-mt-2 flex items-center gap-2 text-[13px]">
            <input
              type="checkbox"
              checked={data.wait_after_enter ?? false}
              onChange={(e) => set({ wait_after_enter: e.target.checked })}
            />
            Then wait for the caller (no LLM reply), e.g. after reading details back
          </label>
          <FieldsEditor fields={data.fields ?? []} onChange={(fields) => set({ fields })} />
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-slate-600">Tools this step may call</span>
            {toolNodes.length === 0 && (
              <span className="text-[11px] text-slate-400">Add an HTTP tool node first.</span>
            )}
            {toolNodes.map((tool) => (
              <label key={tool.id} className="flex items-center gap-2 text-[13px]">
                <input
                  type="checkbox"
                  checked={(data.tools ?? []).includes(tool.id)}
                  onChange={(e) =>
                    set({
                      tools: e.target.checked
                        ? [...(data.tools ?? []), tool.id]
                        : (data.tools ?? []).filter((id) => id !== tool.id),
                    })
                  }
                />
                {tool.data.data.name}
              </label>
            ))}
            <label className="mt-1 flex items-center gap-2 text-[13px]">
              <input
                type="checkbox"
                checked={data.use_knowledge ?? false}
                onChange={(e) => set({ use_knowledge: e.target.checked })}
              />
              Search the agent&apos;s knowledge bases
            </label>
          </div>
        </>
      )}

      {nodeType === "tool" && (
        <>
          <Labelled label="Function name" hint="lowercase_with_underscores; the LLM sees this">
            <input
              className={INPUT}
              value={data.name ?? ""}
              onChange={(e) => set({ name: e.target.value })}
            />
          </Labelled>
          <Labelled label="Description" hint="When to use it and what it returns">
            <input
              className={INPUT}
              value={data.description ?? ""}
              onChange={(e) => set({ description: e.target.value })}
            />
          </Labelled>
          <div className="grid grid-cols-[90px_1fr] gap-2">
            <Labelled label="Method">
              <select
                className={INPUT}
                value={data.method ?? "GET"}
                onChange={(e) => set({ method: e.target.value as "GET" | "POST" })}
              >
                <option>GET</option>
                <option>POST</option>
              </select>
            </Labelled>
            <Labelled label="URL" hint="{field} placeholders are filled from collected fields">
              <input
                className={INPUT}
                value={data.url ?? ""}
                onChange={(e) => set({ url: e.target.value })}
              />
            </Labelled>
          </div>
          {data.method === "POST" && (
            <KeyValueEditor
              label="JSON body"
              rows={data.body ?? {}}
              onChange={(body) => set({ body })}
            />
          )}
          <Labelled
            label="Say while it runs (optional)"
            hint="Spoken only if the call takes more than a moment"
          >
            <input
              className={INPUT}
              value={data.say_while_running ?? ""}
              placeholder="e.g. One moment, let me check."
              onChange={(e) => set({ say_while_running: e.target.value })}
            />
          </Labelled>
          <KeyValueEditor
            label="Save to fields (field ← path in the JSON result)"
            rows={data.save_to_fields ?? {}}
            onChange={(save_to_fields) => set({ save_to_fields })}
          />
          <Labelled
            label="Show the LLM only (optional)"
            hint="Paths in the JSON result, comma-separated; empty shows all of it"
          >
            <ListInput
              key={node.id}
              values={data.result_fields ?? []}
              placeholder="e.g. doctor, free_times"
              onChange={(result_fields) => set({ result_fields })}
            />
          </Labelled>
        </>
      )}

      {nodeType === "end" && (
        <>
          <Labelled label="Outcome" hint="Recorded on the call, e.g. booked, not_interested">
            <input
              className={INPUT}
              value={data.outcome ?? ""}
              onChange={(e) => set({ outcome: e.target.value })}
            />
          </Labelled>
          <Labelled
            label="Last thing the agent says"
            hint="{placeholders} from fields and the last tool result"
          >
            <textarea
              className={`${INPUT} min-h-[70px]`}
              value={data.message ?? ""}
              onChange={(e) => set({ message: e.target.value })}
            />
          </Labelled>
        </>
      )}

      {nodeType === "transfer" && (
        <>
          <Labelled label="What the agent says first">
            <input
              className={INPUT}
              value={data.message ?? ""}
              onChange={(e) => set({ message: e.target.value })}
            />
          </Labelled>
          <Labelled
            label="Transfer to"
            hint="Phone number; transfers work once phone numbers arrive (Phase 4)"
          >
            <input
              className={INPUT}
              value={data.destination ?? ""}
              onChange={(e) => set({ destination: e.target.value })}
            />
          </Labelled>
        </>
      )}

      {nodeType === "global" && (
        <Labelled label="Fires when" hint="Checked at every step, e.g. the caller asks for a human">
          <textarea
            className={`${INPUT} min-h-[60px]`}
            value={data.condition ?? ""}
            onChange={(e) => set({ condition: e.target.value })}
          />
        </Labelled>
      )}

      {nodeType !== "start" && (
        <button
          type="button"
          onClick={onDelete}
          className="mt-2 flex items-center gap-1.5 self-start text-xs text-red-600 hover:underline"
        >
          <Trash2 size={13} /> Delete node
        </button>
      )}
    </div>
  );
}

function FieldsEditor({
  fields,
  onChange,
}: {
  fields: FieldSpec[];
  onChange: (f: FieldSpec[]) => void;
}) {
  const update = (index: number, changes: Partial<FieldSpec>) =>
    onChange(fields.map((field, i) => (i === index ? { ...field, ...changes } : field)));
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-slate-600">Fields to collect</span>
      {fields.map((field, index) => (
        <div key={index} className="flex flex-col gap-1 rounded-lg border border-slate-200 p-2">
          <div className="flex gap-1.5">
            <input
              className={`${INPUT} font-mono text-xs`}
              value={field.name}
              placeholder="field_name"
              onChange={(e) => update(index, { name: e.target.value })}
            />
            <select
              className={`${INPUT} w-24`}
              value={field.type}
              onChange={(e) => update(index, { type: e.target.value as FieldType })}
            >
              {FIELD_TYPES.map((type) => (
                <option key={type}>{type}</option>
              ))}
            </select>
            <button
              type="button"
              aria-label={`Remove ${field.name}`}
              onClick={() => onChange(fields.filter((_, i) => i !== index))}
              className="text-slate-400 hover:text-red-600"
            >
              <Trash2 size={13} />
            </button>
          </div>
          <input
            className={`${INPUT} text-xs`}
            value={field.description}
            placeholder="What it is (the LLM reads this)"
            onChange={(e) => update(index, { description: e.target.value })}
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() =>
          onChange([...fields, { name: "", type: "text", description: "", required: true }])
        }
        className="flex items-center gap-1 self-start text-xs font-medium text-brand-700"
      >
        <Plus size={13} /> Add field
      </button>
    </div>
  );
}

/** A comma-separated list, kept as typed until the input loses focus. */
function ListInput({
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

function KeyValueEditor({
  label,
  rows,
  onChange,
}: {
  label: string;
  rows: Record<string, string>;
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
            onChange={(e) =>
              rebuild(entries.map((entry, i) => (i === index ? [e.target.value, entry[1]] : entry)))
            }
          />
          <input
            className={`${INPUT} font-mono text-xs`}
            value={value}
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

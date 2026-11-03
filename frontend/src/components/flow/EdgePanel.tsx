"use client";

import { Trash2, X } from "lucide-react";

import type { FlowEdgeKind, FlowNodeType } from "@/lib/api";

import { INPUT, Labelled } from "./fields";
import { ALLOWED_EDGE_KINDS, type CanvasEdgeData, EDGE_KIND_LABELS } from "./flowModel";

type Props = {
  sourceType: FlowNodeType;
  data: CanvasEdgeData;
  onChange: (data: CanvasEdgeData) => void;
  onDelete: () => void;
  onClose: () => void;
};

export function EdgePanel({ sourceType, data, onChange, onDelete, onClose }: Props) {
  const kinds = ALLOWED_EDGE_KINDS[sourceType];
  return (
    <div className="flex flex-col gap-3.5 p-4">
      <div className="flex items-center gap-2">
        <h3 className="text-[13px] font-semibold">Edge</h3>
        <button
          type="button"
          onClick={onClose}
          className="ml-auto text-slate-400"
          aria-label="Close"
        >
          <X size={16} />
        </button>
      </div>
      <Labelled label="Take this edge" hint="Conditions are decided by the LLM; the rest by code">
        <select
          className={INPUT}
          value={data.kind}
          onChange={(e) => onChange({ ...data, kind: e.target.value as FlowEdgeKind })}
        >
          {kinds.map((kind) => (
            <option key={kind} value={kind}>
              {EDGE_KIND_LABELS[kind]}
            </option>
          ))}
        </select>
      </Labelled>
      {data.kind === "condition" && (
        <Labelled label="When" hint="e.g. The caller wants to book an appointment">
          <textarea
            className={`${INPUT} min-h-[70px]`}
            value={data.condition}
            onChange={(e) => onChange({ ...data, condition: e.target.value })}
          />
        </Labelled>
      )}
      <button
        type="button"
        onClick={onDelete}
        className="mt-2 flex items-center gap-1.5 self-start text-xs text-red-600 hover:underline"
      >
        <Trash2 size={13} /> Delete edge
      </button>
    </div>
  );
}

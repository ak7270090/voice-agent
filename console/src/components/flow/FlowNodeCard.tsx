"use client";

import { Handle, type NodeProps, Position } from "@xyflow/react";
import clsx from "clsx";

import { type CanvasNode, NODE_META, nodeTitle } from "./flowModel";

const HANDLE_CLASS = "!h-2.5 !w-2.5 !border-2 !border-slate-400 !bg-white";

export function FlowNodeCard({ data, selected }: NodeProps<CanvasNode>) {
  const meta = NODE_META[data.nodeType];
  const fields = data.data.fields ?? [];
  const hasInput = data.nodeType !== "start" && data.nodeType !== "global";
  const hasOutput = data.nodeType !== "end" && data.nodeType !== "transfer";

  return (
    <div
      className={clsx(
        "relative w-[240px] rounded-xl border bg-white px-3 py-2.5 shadow-sm",
        meta.border,
        selected && "ring-2 ring-brand-500 ring-offset-1",
        data.live && "border-2 border-brand-500 shadow-[0_0_0_5px_rgba(99,102,241,0.14)]",
        data.hasIssue && !data.live && "border-amber-400",
      )}
    >
      {data.live && (
        <span className="absolute -top-2.5 right-2.5 rounded-full bg-brand-600 px-2 py-0.5 text-[10px] font-semibold text-white">
          ● Test call here
        </span>
      )}
      {hasInput && <Handle type="target" position={Position.Top} className={HANDLE_CLASS} />}
      <div className="flex items-center gap-2.5">
        <div
          className={clsx(
            "grid h-7 w-7 shrink-0 place-items-center rounded-lg text-[13px]",
            meta.tint,
          )}
        >
          {meta.icon}
        </div>
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">
            {data.nodeType === "tool" ? `${data.data.method ?? "GET"} · tool` : meta.label}
            {data.data.use_knowledge ? " · knowledge" : ""}
          </div>
          <div className="truncate text-[13px] font-semibold">
            {nodeTitle(data.nodeType, data.data)}
          </div>
        </div>
      </div>
      {data.nodeType === "global" && data.data.condition && (
        <p className="mt-1.5 line-clamp-2 text-[11px] text-slate-500">{data.data.condition}</p>
      )}
      {fields.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {fields.map((field) => {
            const have = data.collected.includes(field.name);
            return (
              <span
                key={field.name}
                className={clsx(
                  "rounded-full px-1.5 py-px text-[10px] font-medium",
                  have ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600",
                )}
              >
                {have ? "✓ " : ""}
                {field.name}
              </span>
            );
          })}
        </div>
      )}
      {(data.data.tools?.length ?? 0) > 0 && (
        <div className="mt-1.5 text-[10px] text-sky-700">tools: {data.data.tools?.join(", ")}</div>
      )}
      {hasOutput && <Handle type="source" position={Position.Bottom} className={HANDLE_CLASS} />}
    </div>
  );
}

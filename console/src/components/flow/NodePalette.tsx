import clsx from "clsx";

import type { FlowNodeType } from "@/lib/api";

import { NODE_META, PALETTE } from "./flowModel";

export const DRAG_TYPE = "application/x-studio-node";

export function NodePalette() {
  return (
    <aside className="flex w-52 shrink-0 flex-col gap-1.5 overflow-y-auto border-r border-slate-200 bg-white px-3 py-3.5">
      <p className="px-1 text-[11px] text-slate-400">Drag onto the canvas</p>
      {PALETTE.map(({ group, types }) => (
        <div key={group} className="flex flex-col gap-1.5">
          <div className="px-1 pt-2.5 text-[11px] uppercase tracking-wider text-slate-400">
            {group}
          </div>
          {types.map((type) => (
            <PaletteItem key={type} type={type} />
          ))}
        </div>
      ))}
    </aside>
  );
}

function PaletteItem({ type }: { type: FlowNodeType }) {
  const meta = NODE_META[type];
  return (
    <div
      draggable
      onDragStart={(event) => {
        event.dataTransfer.setData(DRAG_TYPE, type);
        event.dataTransfer.effectAllowed = "move";
      }}
      className="flex cursor-grab select-none items-center gap-2.5 rounded-lg border border-slate-200 bg-white px-2 py-1.5 active:cursor-grabbing"
    >
      <div className={clsx("grid h-7 w-7 place-items-center rounded-md text-[13px]", meta.tint)}>
        {meta.icon}
      </div>
      <div className="text-[13px] leading-tight">
        {meta.label}
        <small className="block text-[11px] text-slate-500">{meta.hint}</small>
      </div>
    </div>
  );
}

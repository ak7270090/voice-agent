import { Trash2 } from "lucide-react";

import { Card, Chip } from "@/components/ui/primitives";
import type { DocumentStatus, KnowledgeDocument } from "@/lib/api";

const STATUS_TONES: Record<DocumentStatus, "neutral" | "amber" | "green" | "red"> = {
  queued: "neutral",
  processing: "amber",
  ready: "green",
  failed: "red",
};

function fileBadge(document: KnowledgeDocument): string {
  if (document.source === "url") return "URL";
  return (document.name.split(".").pop() ?? "file").toUpperCase().slice(0, 4);
}

function size(bytes: number): string {
  if (bytes === 0) return "—";
  return bytes < 1024 * 1024
    ? `${Math.ceil(bytes / 1024)} KB`
    : `${(bytes / 1048576).toFixed(1)} MB`;
}

export function DocumentTable({
  documents,
  onDelete,
}: {
  documents: KnowledgeDocument[];
  onDelete: (document: KnowledgeDocument) => void;
}) {
  return (
    <Card className="overflow-hidden">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/50 text-left text-xs text-slate-500">
            <th className="px-4 py-2 font-medium">Document</th>
            <th className="px-4 py-2 text-right font-medium">Size</th>
            <th className="px-4 py-2 text-right font-medium">Chunks</th>
            <th className="px-4 py-2 font-medium">Status</th>
            <th className="w-10 px-2 py-2" />
          </tr>
        </thead>
        <tbody>
          {documents.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-4 text-slate-400">
                No documents yet.
              </td>
            </tr>
          )}
          {documents.map((document) => (
            <tr key={document.id} className="border-t border-slate-100 align-top text-slate-700">
              <td className="px-4 py-2.5">
                <div className="flex items-center gap-2.5">
                  <span className="grid h-7 w-9 shrink-0 place-items-center rounded-md bg-slate-100 text-[10px] font-bold text-slate-600">
                    {fileBadge(document)}
                  </span>
                  <span className="truncate font-medium text-slate-900">{document.name}</span>
                </div>
                {document.error && (
                  <p className="mt-1 pl-[46px] text-xs text-red-600">{document.error}</p>
                )}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums">{size(document.size_bytes)}</td>
              <td className="px-4 py-2.5 text-right tabular-nums">
                {document.status === "ready" ? document.chunk_count : "—"}
              </td>
              <td className="px-4 py-2.5">
                <Chip tone={STATUS_TONES[document.status]} dot={document.status === "processing"}>
                  {document.status}
                </Chip>
              </td>
              <td className="px-2 py-2.5">
                <button
                  type="button"
                  onClick={() => onDelete(document)}
                  aria-label={`Delete ${document.name}`}
                  className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 size={14} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

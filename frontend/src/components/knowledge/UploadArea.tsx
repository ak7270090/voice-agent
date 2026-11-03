"use client";

import clsx from "clsx";
import { Link2, Upload } from "lucide-react";
import { type DragEvent, type FormEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/primitives";

const ACCEPTED_TYPES = ".pdf,.docx,.pptx,.xlsx,.html,.htm,.md,.txt,.csv";

export function UploadArea({
  busy,
  onFiles,
  onUrl,
}: {
  busy: boolean;
  onFiles: (files: File[]) => void;
  onUrl: (url: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [url, setUrl] = useState("");

  function drop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    onFiles([...event.dataTransfer.files]);
  }

  function submitUrl(event: FormEvent) {
    event.preventDefault();
    if (url.trim()) onUrl(url.trim());
    setUrl("");
  }

  return (
    <div className="flex flex-col gap-3">
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
        disabled={busy}
        className={clsx(
          "flex flex-col items-center gap-1.5 rounded-xl border-[1.5px] border-dashed px-6 py-6 text-[13px] text-slate-500",
          dragging ? "border-brand-500 bg-brand-50" : "border-brand-100 bg-white",
        )}
      >
        <Upload size={20} className="text-brand-600" />
        <span className="text-sm font-semibold text-slate-900">
          {busy ? "Uploading…" : "Drop files here, or click to choose"}
        </span>
        PDF, Word, PowerPoint, Excel, HTML, Markdown or text · up to 20 MB
      </button>
      <input
        ref={input}
        type="file"
        multiple
        accept={ACCEPTED_TYPES}
        hidden
        onChange={(event) => {
          onFiles([...(event.target.files ?? [])]);
          event.target.value = "";
        }}
      />
      <form onSubmit={submitUrl} className="flex gap-2">
        <div className="flex flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3">
          <Link2 size={14} className="text-slate-400" />
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="Or add a web page: https://…"
            className="flex-1 py-1.5 text-[13px] outline-none"
          />
        </div>
        <Button type="submit" disabled={!url.trim() || busy}>
          Add URL
        </Button>
      </form>
    </div>
  );
}

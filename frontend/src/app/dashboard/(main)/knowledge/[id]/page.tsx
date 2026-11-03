"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DocumentTable } from "@/components/knowledge/DocumentTable";
import { TrySearch } from "@/components/knowledge/TrySearch";
import { UploadArea } from "@/components/knowledge/UploadArea";
import { Button, Card, PageHeader } from "@/components/ui/primitives";
import {
  addUrlDocument,
  deleteDocument,
  deleteKnowledgeBase,
  type KnowledgeBase,
  type KnowledgeDocument,
  listDocuments,
  listKnowledgeBases,
  uploadDocument,
} from "@/lib/api";
import { dashboardPath } from "@/lib/paths";

// Poll while a document is still being read and embedded.
const REFRESH_WHILE_PROCESSING_MS = 2000;
const IN_PROGRESS = new Set(["queued", "processing"]);

export default function KnowledgeBasePage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [bases, latest] = await Promise.all([listKnowledgeBases(), listDocuments(params.id)]);
    setKnowledgeBase(bases.find((base) => base.id === params.id) ?? null);
    setDocuments(latest);
  }, [params.id]);

  useEffect(() => {
    refresh().catch((cause: Error) => setError(cause.message));
  }, [refresh]);

  const processing = documents.some((document) => IN_PROGRESS.has(document.status));
  useEffect(() => {
    if (!processing) return;
    const timer = setInterval(() => refresh().catch(() => undefined), REFRESH_WHILE_PROCESSING_MS);
    return () => clearInterval(timer);
  }, [processing, refresh]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const uploadFiles = (files: File[]) =>
    run(async () => {
      for (const file of files) await uploadDocument(params.id, file);
    });

  async function removeKnowledgeBase() {
    if (!window.confirm("Delete this knowledge base and all its documents?")) return;
    await deleteKnowledgeBase(params.id);
    router.push(dashboardPath("/knowledge"));
  }

  const totalChunks = documents.reduce((sum, document) => sum + document.chunk_count, 0);

  return (
    <>
      <PageHeader>
        <Link href={dashboardPath("/knowledge")} className="text-slate-500 hover:text-slate-700">
          Knowledge
        </Link>
        <span className="text-slate-300">/</span>
        <span className="font-semibold">{knowledgeBase?.name ?? "…"}</span>
        <span className="ml-auto">
          <Button variant="danger" onClick={removeKnowledgeBase}>
            Delete
          </Button>
        </span>
      </PageHeader>
      <div className="flex flex-col gap-4 p-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{knowledgeBase?.name}</h1>
          <p className="mt-1 text-[13px] text-slate-500">
            {documents.length} documents · {totalChunks} chunks · link it to agents on their page
          </p>
        </div>
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.6fr_1fr]">
          <div className="flex flex-col gap-4">
            <UploadArea
              busy={busy}
              onFiles={uploadFiles}
              onUrl={(url) => run(() => addUrlDocument(params.id, url))}
            />
            <DocumentTable
              documents={documents}
              onDelete={(document) => run(() => deleteDocument(params.id, document.id))}
            />
            <Card className="px-4 py-3 text-xs leading-relaxed text-slate-500">
              Files are read into Markdown (MarkItDown), split into chunks of about 800 characters,
              embedded with text-embedding-3-small and stored in Postgres (pgvector). Scanned PDFs
              without a text layer are not supported yet.
            </Card>
          </div>
          <TrySearch knowledgeBaseId={params.id} />
        </div>
      </div>
    </>
  );
}

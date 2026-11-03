"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

import { Button, Card, Chip, PageHeader } from "@/components/ui/primitives";
import { createKnowledgeBase, type KnowledgeBase, listKnowledgeBases } from "@/lib/api";
import { dashboardPath } from "@/lib/navigation";

export default function KnowledgePage() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listKnowledgeBases()
      .then(setKnowledgeBases)
      .catch((cause: Error) => setError(cause.message));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    try {
      const created = await createKnowledgeBase(name.trim());
      setKnowledgeBases((current) => [created, ...(current ?? [])]);
      setName("");
    } catch (cause) {
      setError((cause as Error).message);
    }
  }

  return (
    <>
      <PageHeader>
        <span className="font-semibold">Knowledge</span>
      </PageHeader>
      <div className="flex flex-col gap-5 p-6">
        <div className="flex items-end gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Knowledge bases</h1>
            <p className="mt-1 text-[13px] text-slate-500">
              Upload documents once; every agent linked to a knowledge base can answer from it.
            </p>
          </div>
          <form onSubmit={create} className="ml-auto flex gap-2">
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="New knowledge base name"
              className="w-64 rounded-lg border border-slate-200 px-3 py-1.5 text-[13px] outline-none focus:border-brand-500"
            />
            <Button type="submit" variant="primary" disabled={!name.trim()}>
              Create
            </Button>
          </form>
        </div>
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}
        {knowledgeBases?.length === 0 && (
          <p className="text-[13px] text-slate-500">No knowledge bases yet. Create one above.</p>
        )}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {knowledgeBases?.map((knowledgeBase) => (
            <Link key={knowledgeBase.id} href={dashboardPath(`/knowledge/${knowledgeBase.id}`)}>
              <Card className="flex flex-col gap-3 p-4 hover:border-brand-500">
                <div className="flex items-center gap-2.5">
                  <div className="grid h-10 w-10 place-items-center rounded-lg bg-violet-50 text-lg text-violet-600">
                    ▤
                  </div>
                  <span className="text-sm font-semibold">{knowledgeBase.name}</span>
                </div>
                <div className="flex gap-1.5">
                  <Chip>{knowledgeBase.document_count} documents</Chip>
                  <Chip>{knowledgeBase.chunk_count} chunks</Chip>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}

"use client";

import { Search } from "lucide-react";
import { type FormEvent, useState } from "react";

import { Card, Chip } from "@/components/ui/primitives";
import { type SearchHit, searchKnowledgeBase } from "@/lib/api";

export function TrySearch({ knowledgeBaseId }: { knowledgeBaseId: string }) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      setHits(await searchKnowledgeBase(knowledgeBaseId, query.trim()));
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setSearching(false);
    }
  }

  return (
    <Card className="flex flex-col">
      <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
        <h3 className="text-[13px] font-semibold">Try a question</h3>
        <span className="text-[13px] text-slate-500">what the agent would find</span>
      </div>
      <div className="flex flex-col gap-3 p-4">
        <form onSubmit={search} className="flex gap-2">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="e.g. Is the skin doctor available on Sunday?"
            className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-[13px] outline-none focus:border-brand-500"
          />
          <button
            type="submit"
            disabled={searching || !query.trim()}
            aria-label="Search"
            className="grid w-9 place-items-center rounded-lg bg-brand-600 text-white disabled:bg-slate-200"
          >
            <Search size={15} />
          </button>
        </form>
        {error && <p className="text-xs text-red-600">{error}</p>}
        {hits?.length === 0 && (
          <p className="text-[13px] text-slate-500">
            Nothing found: the agent would say it does not know.
          </p>
        )}
        {hits?.map((hit, index) => (
          <div
            key={`${hit.document_id}-${index}`}
            className="rounded-lg border border-slate-200 p-3"
          >
            <div className="mb-1.5 flex items-center gap-2 text-[11px] text-slate-500">
              <span className="truncate">{hit.document_name}</span>
              <span className="ml-auto">
                <Chip tone={index === 0 ? "green" : "neutral"}>{hit.score.toFixed(2)}</Chip>
              </span>
            </div>
            <p className="whitespace-pre-line text-[13px] leading-relaxed text-slate-800">
              {hit.text}
            </p>
            <p className="mt-1.5 text-[11px] text-slate-400">
              similarity {hit.similarity.toFixed(2)} · keyword overlap{" "}
              {hit.keyword_overlap.toFixed(2)}
            </p>
          </div>
        ))}
        <p className="border-t border-slate-100 pt-3 text-xs text-slate-500">
          Score = vector similarity plus a small bonus for the question&apos;s words found in the
          chunk. The best few chunks go to the agent.
        </p>
      </div>
    </Card>
  );
}

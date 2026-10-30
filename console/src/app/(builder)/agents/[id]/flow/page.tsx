"use client";

import { useEffect, useState } from "react";

import { FlowBuilder } from "@/components/flow/FlowBuilder";
import { type Agent, type FlowDraft, getAgent, getFlow } from "@/lib/api";

export default function FlowPage({ params }: { params: { id: string } }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [draft, setDraft] = useState<FlowDraft | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getAgent(params.id), getFlow(params.id)])
      .then(([loadedAgent, loadedDraft]) => {
        setAgent(loadedAgent);
        setDraft(loadedDraft);
      })
      .catch((cause: Error) => setError(cause.message));
  }, [params.id]);

  if (error) return <p className="p-6 text-[13px] text-red-600">{error}</p>;
  if (!agent || !draft) return <p className="p-6 text-[13px] text-slate-400">Loading flow…</p>;
  return <FlowBuilder agent={agent} initial={draft} />;
}

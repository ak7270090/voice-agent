"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AgentEditor } from "@/components/agents/AgentEditor";
import { RecentCalls } from "@/components/agents/RecentCalls";
import { TestCallPanel } from "@/components/test-call/TestCallPanel";
import { Button, Chip, PageHeader } from "@/components/ui/primitives";
import {
  type Agent,
  type AgentUpdate,
  type Call,
  getAgent,
  listCalls,
  updateAgent,
} from "@/lib/api";

// The runtime closes the call record a moment after the room empties.
const CALL_RECORD_DELAY_MS = 1500;

export default function AgentPage({ params }: { params: { id: string } }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [calls, setCalls] = useState<Call[]>([]);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<{ tone: "green" | "red"; text: string } | null>(null);

  const refreshCalls = useCallback(() => {
    listCalls(params.id)
      .then(setCalls)
      .catch(() => undefined);
  }, [params.id]);

  useEffect(() => {
    getAgent(params.id)
      .then(setAgent)
      .catch((cause: Error) => setNotice({ tone: "red", text: cause.message }));
    refreshCalls();
  }, [params.id, refreshCalls]);

  const onCallEnded = useCallback(() => {
    setTimeout(refreshCalls, CALL_RECORD_DELAY_MS);
  }, [refreshCalls]);

  async function save(changes: AgentUpdate) {
    setSaving(true);
    try {
      setAgent(await updateAgent(params.id, changes));
      setNotice({ tone: "green", text: "Saved. The next test call uses the new settings." });
    } catch (cause) {
      setNotice({ tone: "red", text: `Could not save: ${(cause as Error).message}` });
    } finally {
      setSaving(false);
    }
  }

  async function toggleLive() {
    if (agent) await save({ status: agent.status === "live" ? "draft" : "live" });
  }

  return (
    <>
      <PageHeader>
        <Link href="/agents" className="text-slate-500 hover:text-slate-700">
          Agents
        </Link>
        <span className="text-slate-300">/</span>
        <span className="font-semibold">{agent?.name ?? "…"}</span>
        {agent &&
          (agent.status === "live" ? (
            <Chip tone="green" dot>
              Live
            </Chip>
          ) : (
            <Chip tone="amber">Draft</Chip>
          ))}
        {agent && (
          <span className="ml-auto">
            <Button onClick={toggleLive} disabled={saving}>
              {agent.status === "live" ? "Move to draft" : "Mark as live"}
            </Button>
          </span>
        )}
      </PageHeader>
      <div className="flex flex-col gap-4 p-6">
        {notice && (
          <p
            className={`rounded-lg px-3 py-2 text-[13px] ${notice.tone === "green" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"}`}
          >
            {notice.text}
          </p>
        )}
        {agent && (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_380px]">
            <div className="flex flex-col gap-4">
              <AgentEditor key={agent.updated_at} agent={agent} saving={saving} onSave={save} />
              <RecentCalls calls={calls} />
            </div>
            <TestCallPanel agentId={agent.id} onCallEnded={onCallEnded} />
          </div>
        )}
      </div>
    </>
  );
}

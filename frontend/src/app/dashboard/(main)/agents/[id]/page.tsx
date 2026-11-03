"use client";

import { Workflow } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AgentEditor } from "@/components/agents/AgentEditor";
import { CallMe } from "@/components/agents/CallMe";
import { CallTable } from "@/components/calls/CallTable";
import { TestCallPanel } from "@/components/test-call/TestCallPanel";
import { Button, Card, Chip, PageHeader } from "@/components/ui/primitives";
import {
  type Agent,
  type AgentUpdate,
  type Call,
  getAgent,
  type KnowledgeBase,
  listCalls,
  listKnowledgeBases,
  updateAgent,
} from "@/lib/api";
import { dashboardPath } from "@/lib/navigation";

// The runtime closes the call record a moment after the room empties.
const CALL_RECORD_DELAY_MS = 1500;

export default function AgentPage({ params }: { params: { id: string } }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [calls, setCalls] = useState<Call[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
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
    listKnowledgeBases()
      .then(setKnowledgeBases)
      .catch(() => undefined);
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
        <Link href={dashboardPath("/agents")} className="text-slate-500 hover:text-slate-700">
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
          <span className="ml-auto flex items-center gap-2">
            <Link
              href={dashboardPath(`/agents/${agent.id}/flow`)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-brand-600 bg-brand-600 px-3 py-1.5 text-[13px] font-medium text-white hover:bg-brand-700"
            >
              <Workflow size={14} /> {agent.has_flow ? "Open flow builder" : "Create a flow"}
            </Link>
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
              <AgentEditor
                key={agent.updated_at}
                agent={agent}
                knowledgeBases={knowledgeBases}
                saving={saving}
                onSave={save}
              />
              <Card>
                <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
                  <h3 className="text-[13px] font-semibold">Recent calls</h3>
                  <Chip>{calls.length}</Chip>
                  <Link
                    href={dashboardPath(`/calls?agent_id=${agent.id}`)}
                    className="ml-auto text-xs text-brand-600 hover:underline"
                  >
                    All calls
                  </Link>
                </div>
                <CallTable calls={calls} />
              </Card>
            </div>
            <div className="flex flex-col gap-4 self-start xl:sticky xl:top-6">
              <TestCallPanel agentId={agent.id} onCallEnded={onCallEnded} />
              <CallMe agentId={agent.id} onCallStarted={onCallEnded} />
            </div>
          </div>
        )}
      </div>
    </>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";

import { CallTable } from "@/components/calls/CallTable";
import { Card, PageHeader } from "@/components/ui/primitives";
import { type Agent, type Call, type CallFilters, listAgents, listAllCalls } from "@/lib/api";

const SELECT =
  "rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[13px] outline-none focus:border-brand-500";

export default function CallsPage({ searchParams }: { searchParams: { agent_id?: string } }) {
  const [filters, setFilters] = useState<CallFilters>({ agent_id: searchParams.agent_id });
  const [calls, setCalls] = useState<Call[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    listAllCalls(filters)
      .then(setCalls)
      .catch((cause: Error) => setError(cause.message));
  }, [filters]);

  const agentNames = useMemo(
    () => Object.fromEntries(agents.map((agent) => [agent.id, agent.name])),
    [agents],
  );
  const set = (changes: CallFilters) => setFilters((current) => ({ ...current, ...changes }));

  return (
    <>
      <PageHeader>
        <span className="font-semibold">Calls</span>
      </PageHeader>
      <div className="flex flex-col gap-4 p-6">
        <div className="flex flex-wrap items-center gap-2">
          <select
            className={SELECT}
            value={filters.agent_id ?? ""}
            onChange={(e) => set({ agent_id: e.target.value || undefined })}
          >
            <option value="">All agents</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
          <select
            className={SELECT}
            value={filters.channel ?? ""}
            onChange={(e) => set({ channel: e.target.value || undefined })}
          >
            <option value="">Web and phone</option>
            <option value="web">Web</option>
            <option value="phone">Phone</option>
          </select>
          <select
            className={SELECT}
            value={filters.direction ?? ""}
            onChange={(e) => set({ direction: e.target.value || undefined })}
          >
            <option value="">Both directions</option>
            <option value="inbound">Inbound</option>
            <option value="outbound">Outbound</option>
          </select>
          <input
            className={SELECT}
            placeholder="Outcome, e.g. booked"
            value={filters.outcome ?? ""}
            onChange={(e) => set({ outcome: e.target.value.trim() || undefined })}
          />
        </div>
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}
        <Card>
          <CallTable calls={calls} agentNames={agentNames} />
        </Card>
      </div>
    </>
  );
}

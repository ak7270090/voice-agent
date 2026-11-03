"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AgentCard, TemplateCard } from "@/components/agents/AgentCards";
import { Chip, PageHeader } from "@/components/ui/primitives";
import {
  type Agent,
  type AgentTemplate,
  createAgentFromTemplate,
  listAgents,
  listTemplates,
} from "@/lib/api";
import { dashboardPath } from "@/lib/paths";

export default function AgentsPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [creating, setCreating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listTemplates(), listAgents()])
      .then(([loadedTemplates, loadedAgents]) => {
        setTemplates(loadedTemplates);
        setAgents(loadedAgents);
      })
      .catch((cause: Error) => setError(`Could not load agents: ${cause.message}`));
  }, []);

  async function startFromTemplate(templateId: string) {
    setCreating(templateId);
    try {
      const agent = await createAgentFromTemplate(templateId);
      router.push(dashboardPath(`/agents/${agent.id}`));
    } catch (cause) {
      setError(`Could not create the agent: ${(cause as Error).message}`);
      setCreating(null);
    }
  }

  return (
    <>
      <PageHeader>
        <span className="font-semibold">Agents</span>
      </PageHeader>
      <div className="flex flex-col gap-5 p-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Agents</h1>
          <p className="mt-1 text-[13px] text-slate-500">
            Each agent has its own instructions, voice and languages. Start from a template, then
            edit and test it in the browser.
          </p>
        </div>
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}

        <section>
          <h2 className="mb-2.5 text-[13px] font-semibold">Start from a template</h2>
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            {templates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                busy={creating === template.id}
                onUse={() => startFromTemplate(template.id)}
              />
            ))}
          </div>
        </section>

        <section>
          <div className="mb-2.5 flex items-center gap-2">
            <h2 className="text-[13px] font-semibold">Your agents</h2>
            {agents && <Chip>{agents.length}</Chip>}
          </div>
          {agents?.length === 0 && (
            <p className="text-[13px] text-slate-500">No agents yet. Pick a template above.</p>
          )}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {agents?.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        </section>
      </div>
    </>
  );
}

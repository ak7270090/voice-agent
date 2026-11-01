import Link from "next/link";

import { Card, Chip } from "@/components/ui/primitives";
import type { Agent, AgentTemplate } from "@/lib/api";
import {
  DEFAULT_TEMPLATE_STYLE,
  LANGUAGE_LABELS,
  llmLabel,
  TEMPLATE_STYLES,
  voiceLabel,
} from "@/lib/constants";

function TemplateIcon({
  templateId,
  size,
}: {
  templateId: string | null;
  size: "large" | "small";
}) {
  const style = (templateId && TEMPLATE_STYLES[templateId]) || DEFAULT_TEMPLATE_STYLE;
  const box = size === "large" ? "h-[74px] w-full text-2xl" : "h-10 w-10 text-lg";
  return (
    <div className={`grid shrink-0 place-items-center rounded-lg ${box} ${style.tint}`}>
      {style.icon}
    </div>
  );
}

export function TemplateCard({
  template,
  busy,
  onUse,
}: {
  template: AgentTemplate;
  busy: boolean;
  onUse: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onUse}
      disabled={busy}
      className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-3.5 text-left hover:border-brand-500 disabled:opacity-60"
    >
      <TemplateIcon templateId={template.id} size="large" />
      <span className="text-[13px] font-semibold">{template.name}</span>
      <span className="text-[13px] leading-snug text-slate-500">{template.summary}</span>
      <span className="mt-auto">
        <Chip tone="brand">{busy ? "Creating…" : template.channel_label}</Chip>
      </span>
    </button>
  );
}

export function AgentCard({ agent }: { agent: Agent }) {
  const speech = agent.language_settings[agent.languages[0]];
  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2.5">
        <TemplateIcon templateId={agent.template} size="small" />
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{agent.name}</div>
          <div className="truncate text-[13px] text-slate-500">
            {llmLabel(agent.llm_model)} ·{" "}
            {speech ? voiceLabel(speech.tts_model, speech.voice) : "no voice"}
          </div>
        </div>
        <span className="ml-auto">
          {agent.status === "live" ? (
            <Chip tone="green" dot>
              Live
            </Chip>
          ) : (
            <Chip>Draft</Chip>
          )}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {agent.languages.map((code) => (
          <Chip key={code}>{LANGUAGE_LABELS[code] ?? code}</Chip>
        ))}
        {agent.has_flow && (
          <Chip tone="brand">
            {agent.published_flow_version ? `Flow v${agent.published_flow_version}` : "Flow draft"}
          </Chip>
        )}
      </div>
      <p className="line-clamp-2 text-[13px] text-slate-600">{agent.greeting}</p>
      <div className="flex items-center gap-2 border-t border-slate-100 pt-3">
        <Link
          href={`/agents/${agent.id}`}
          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Edit and test
        </Link>
        <span className="ml-auto text-xs text-slate-400">
          Updated {new Date(agent.updated_at).toLocaleString()}
        </span>
      </div>
    </Card>
  );
}

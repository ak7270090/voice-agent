"use client";

import { ExternalLink } from "lucide-react";
import Link from "next/link";
import { type ReactNode, useEffect, useState } from "react";

import { SuccessChip } from "@/components/calls/CallTable";
import { Deliveries } from "@/components/calls/Deliveries";
import {
  callSeconds,
  channelLabel,
  formatCost,
  formatSeconds,
  offsetFromStart,
  outcomeLabel,
} from "@/components/calls/format";
import { Card, Chip, PageHeader } from "@/components/ui/primitives";
import { type Agent, type Call, getAgent, getCall } from "@/lib/api";

// While the post-call analysis runs, look again this often.
const ANALYSIS_POLL_MS = 3000;
const COST_PARTS = [
  ["llm", "LLM"],
  ["stt", "Speech-to-text"],
  ["tts", "Voice"],
  ["phone", "Phone"],
  ["analysis", "Post-call analysis"],
] as const;

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <h2 className="border-b border-slate-100 px-4 py-3 text-[13px] font-semibold">{title}</h2>
      <div className="p-4 text-[13px]">{children}</div>
    </Card>
  );
}

function Value({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span className="text-slate-400">—</span>;
  if (typeof value === "boolean") return <>{value ? "yes" : "no"}</>;
  return <>{String(value)}</>;
}

function Analysis({ call }: { call: Call }) {
  if (call.analysis_status === "skipped") {
    return <p className="text-slate-400">Skipped: the caller never spoke.</p>;
  }
  if (call.analysis_status === "failed") {
    return <p className="text-red-600">The analysis failed; see the worker logs.</p>;
  }
  if (call.analysis_status !== "done") return <p className="text-slate-400">Analysing…</p>;
  const { analysis } = call;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-slate-700">{analysis.summary}</p>
      <div className="flex flex-wrap items-center gap-2">
        <SuccessChip call={call} />
        <span className="text-xs text-slate-500">{analysis.success_reason}</span>
      </div>
      <div className="flex flex-wrap gap-4 text-xs text-slate-600">
        <span>Sentiment: {analysis.sentiment}</span>
        <span>
          QA score: <span className="font-semibold">{analysis.qa_score}/5</span>{" "}
          {analysis.qa_notes && <span className="text-slate-500">({analysis.qa_notes})</span>}
        </span>
      </div>
      {analysis.fields && Object.keys(analysis.fields).length > 0 && (
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-xs">
          {Object.entries(analysis.fields).map(([name, value]) => (
            <div key={name} className="contents">
              <dt className="text-slate-500">{name}</dt>
              <dd>
                <Value value={value} />
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

export default function CallPage({ params }: { params: { id: string } }) {
  const [call, setCall] = useState<Call | null>(null);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCall(params.id)
      .then((loaded) => {
        setCall(loaded);
        getAgent(loaded.agent_id)
          .then(setAgent)
          .catch(() => undefined);
      })
      .catch((cause: Error) => setError(cause.message));
  }, [params.id]);

  const waiting = call?.status === "active" || call?.analysis_status === "pending";
  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(() => {
      getCall(params.id)
        .then(setCall)
        .catch(() => undefined);
    }, ANALYSIS_POLL_MS);
    return () => clearInterval(timer);
  }, [waiting, params.id]);

  return (
    <>
      <PageHeader>
        <Link href="/calls" className="text-slate-500 hover:text-slate-700">
          Calls
        </Link>
        <span className="text-slate-300">/</span>
        <span className="font-semibold">
          {call ? new Date(call.started_at).toLocaleString() : "…"}
        </span>
        {call?.outcome && <Chip tone="brand">{outcomeLabel(call.outcome)}</Chip>}
        {call && (
          <span className="ml-auto flex items-center gap-3 text-[13px]">
            {call.recording_url && (
              <a
                href={call.recording_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-brand-600 hover:underline"
              >
                Recording (LiveKit) <ExternalLink size={12} />
              </a>
            )}
            {call.langfuse_url && (
              <a
                href={call.langfuse_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-brand-600 hover:underline"
              >
                Trace (Langfuse) <ExternalLink size={12} />
              </a>
            )}
          </span>
        )}
      </PageHeader>
      <div className="flex flex-col gap-4 p-6">
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}
        {call && (
          <>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
              <span>
                Agent:{" "}
                <Link href={`/agents/${call.agent_id}`} className="text-brand-600 hover:underline">
                  {agent?.name ?? "…"}
                </Link>
              </span>
              <span>{channelLabel(call)}</span>
              <span>Duration {formatSeconds(callSeconds(call))}</span>
              <span>{call.interruptions} interruptions</span>
              {call.campaign_contact_id && <span>Campaign call</span>}
            </div>
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_380px]">
              <div className="flex flex-col gap-4">
                <Section title="Analysis">
                  <Analysis call={call} />
                </Section>
                <Section title="Transcript">
                  {call.transcript.length === 0 ? (
                    <p className="text-slate-400">Nothing was said.</p>
                  ) : (
                    <ol className="flex flex-col gap-2">
                      {call.transcript.map((turn, index) => (
                        <li key={index} className="grid grid-cols-[3rem_5rem_1fr] gap-2">
                          <span className="text-xs tabular-nums text-slate-400">
                            {offsetFromStart(call, turn.at)}
                          </span>
                          <span
                            className={`text-xs font-medium ${turn.role === "assistant" ? "text-brand-600" : "text-slate-500"}`}
                          >
                            {turn.role === "assistant" ? "Agent" : "Caller"}
                          </span>
                          <span className="text-slate-700">{turn.text}</span>
                        </li>
                      ))}
                    </ol>
                  )}
                </Section>
                <Section title="Tool calls">
                  {call.tool_calls.length === 0 ? (
                    <p className="text-slate-400">No tools were called.</p>
                  ) : (
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-slate-500">
                          <th className="pb-1 font-medium">At</th>
                          <th className="pb-1 font-medium">Tool</th>
                          <th className="pb-1 font-medium">Asked by</th>
                          <th className="pb-1 font-medium">Result</th>
                          <th className="pb-1 text-right font-medium">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {call.tool_calls.map((tool, index) => (
                          <tr key={index} className="border-t border-slate-100 align-top">
                            <td className="py-1.5 tabular-nums text-slate-400">
                              {offsetFromStart(call, tool.at)}
                            </td>
                            <td className="py-1.5 font-medium">{tool.name}</td>
                            <td className="py-1.5">{tool.by === "llm" ? "LLM" : "flow"}</td>
                            <td className="max-w-md py-1.5">
                              <Chip tone={tool.ok ? "green" : "red"}>
                                {tool.ok ? "ok" : tool.unavailable ? "no answer" : "failed"}
                              </Chip>{" "}
                              <code className="break-all text-[11px] text-slate-500">
                                {tool.result}
                              </code>
                            </td>
                            <td className="py-1.5 text-right tabular-nums">{tool.ms} ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </Section>
              </div>
              <div className="flex flex-col gap-4">
                <Deliveries callId={call.id} />
                <Section title="Cost">
                  <dl className="grid grid-cols-[1fr_max-content] gap-y-1">
                    {COST_PARTS.map(([key, label]) => (
                      <div key={key} className="contents">
                        <dt className="text-slate-500">{label}</dt>
                        <dd className="text-right tabular-nums">{formatCost(call.cost[key])}</dd>
                      </div>
                    ))}
                    <dt className="border-t border-slate-100 pt-1 font-semibold">Total</dt>
                    <dd className="border-t border-slate-100 pt-1 text-right font-semibold tabular-nums">
                      {formatCost(call.cost.total)}
                    </dd>
                  </dl>
                  {call.cost.llm_unpriced && (
                    <p className="mt-2 text-xs text-amber-700">
                      The agent&apos;s LLM has no price set, so its cost is not included.
                    </p>
                  )}
                  <p className="mt-2 text-xs text-slate-400">
                    {call.usage.llm_input_tokens ?? 0} input + {call.usage.llm_output_tokens ?? 0}{" "}
                    output tokens · {call.usage.stt_seconds ?? 0} s heard ·{" "}
                    {call.usage.tts_characters ?? 0} characters spoken
                  </p>
                </Section>
                <Section title="Collected">
                  {Object.keys(call.fields).length === 0 ? (
                    <p className="text-slate-400">Nothing collected.</p>
                  ) : (
                    <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-xs">
                      {Object.entries(call.fields).map(([name, value]) => (
                        <div key={name} className="contents">
                          <dt className="text-slate-500">{name}</dt>
                          <dd>
                            <Value value={value} />
                          </dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  {call.flow_path.length > 0 && (
                    <p className="mt-3 text-xs text-slate-400">
                      Path: {call.flow_path.join(" → ")}
                    </p>
                  )}
                </Section>
                <Section title="Reply delay per turn">
                  {call.turn_latency_ms.length === 0 ? (
                    <p className="text-slate-400">No voice turns (a typed call).</p>
                  ) : (
                    <ol className="flex flex-col gap-1 text-xs tabular-nums">
                      {call.turn_latency_ms.map((turn, index) => (
                        <li key={index} className="flex justify-between">
                          <span className="text-slate-500">Turn {index + 1}</span>
                          <span>
                            {turn.e2e_latency !== undefined
                              ? `${(turn.e2e_latency / 1000).toFixed(2)} s`
                              : "—"}
                          </span>
                        </li>
                      ))}
                    </ol>
                  )}
                </Section>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}

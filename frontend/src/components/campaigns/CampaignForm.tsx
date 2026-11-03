"use client";

import Link from "next/link";
import { type FormEvent, type ReactNode, useState } from "react";

import { Button, Card, TimeZoneSelect } from "@/components/ui/primitives";
import type { Agent, CampaignSettings, PhoneNumber } from "@/lib/api";
import { dashboardPath } from "@/lib/paths";

const INPUT =
  "w-full rounded-lg border border-slate-200 px-3 py-1.5 text-[13px] outline-none focus:border-brand-500";

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      {children}
      {hint && <span className="text-[11px] text-slate-400">{hint}</span>}
    </label>
  );
}

export function CampaignForm({
  agents,
  numbers,
  onCreate,
}: {
  agents: Agent[];
  numbers: PhoneNumber[];
  onCreate: (settings: CampaignSettings) => Promise<void>;
}) {
  const callers = numbers.filter((number) => number.can_call_out);
  const [settings, setSettings] = useState<CampaignSettings>({
    name: "",
    agent_id: agents[0]?.id ?? "",
    from_number_id: callers[0]?.id ?? "",
    window_start: "09:00",
    window_end: "20:00",
    timezone: "Asia/Kolkata",
    max_concurrent: 2,
    max_attempts: 3,
    retry_after_minutes: 30,
  });
  const [creating, setCreating] = useState(false);
  const set = (changes: Partial<CampaignSettings>) =>
    setSettings((current) => ({ ...current, ...changes }));
  const agentId = settings.agent_id || agents[0]?.id || "";
  const fromId = settings.from_number_id || callers[0]?.id || "";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    await onCreate({ ...settings, agent_id: agentId, from_number_id: fromId });
    setCreating(false);
  }

  if (callers.length === 0) {
    return (
      <Card className="p-4 text-[13px] text-slate-500">
        A campaign calls from a number with an outbound trunk.{" "}
        <Link href={dashboardPath("/numbers")} className="text-brand-600 hover:underline">
          Add one
        </Link>{" "}
        first.
      </Card>
    );
  }

  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-4 p-4">
        <h2 className="text-[13px] font-semibold">New campaign</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Field label="Name">
            <input
              className={INPUT}
              value={settings.name}
              placeholder="Tomorrow's reminders"
              onChange={(e) => set({ name: e.target.value })}
            />
          </Field>
          <Field label="Agent" hint="Runs its published flow">
            <select
              className={INPUT}
              value={agentId}
              onChange={(e) => set({ agent_id: e.target.value })}
            >
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Calls from">
            <select
              className={INPUT}
              value={fromId}
              onChange={(e) => set({ from_number_id: e.target.value })}
            >
              {callers.map((number) => (
                <option key={number.id} value={number.id}>
                  {number.number} {number.label && `(${number.label})`}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-6">
          <Field label="Calls from (time)">
            <input
              type="time"
              className={INPUT}
              value={settings.window_start}
              onChange={(e) => set({ window_start: e.target.value })}
            />
          </Field>
          <Field label="Until">
            <input
              type="time"
              className={INPUT}
              value={settings.window_end}
              onChange={(e) => set({ window_end: e.target.value })}
            />
          </Field>
          <Field label="Time zone">
            <TimeZoneSelect
              className={INPUT}
              value={settings.timezone}
              onChange={(timezone) => set({ timezone })}
            />
          </Field>
          <Field label="Calls at once" hint="LiveKit free plan: 5 sessions">
            <input
              type="number"
              min={1}
              max={5}
              className={INPUT}
              value={settings.max_concurrent}
              onChange={(e) => set({ max_concurrent: Number(e.target.value) })}
            />
          </Field>
          <Field label="Tries per contact">
            <input
              type="number"
              min={1}
              max={5}
              className={INPUT}
              value={settings.max_attempts}
              onChange={(e) => set({ max_attempts: Number(e.target.value) })}
            />
          </Field>
          <Field label="Retry after (min)" hint="If nobody answered">
            <input
              type="number"
              min={1}
              className={INPUT}
              value={settings.retry_after_minutes}
              onChange={(e) => set({ retry_after_minutes: Number(e.target.value) })}
            />
          </Field>
        </div>
        <div className="flex justify-end">
          <Button type="submit" variant="primary" disabled={creating || !settings.name.trim()}>
            {creating ? "Creating…" : "Create campaign"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

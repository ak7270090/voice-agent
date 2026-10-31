"use client";

import { type FormEvent, type ReactNode, useState } from "react";

import { Button, Card } from "@/components/ui/primitives";
import type { Agent, PhoneNumberCreate, PhoneProvider } from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-slate-200 px-3 py-1.5 text-[13px] outline-none focus:border-brand-500";

const PROVIDERS: { value: PhoneProvider; label: string; hint: string }[] = [
  {
    value: "livekit",
    label: "LiveKit number",
    hint: "Rented in the LiveKit dashboard. Answers calls only; no calling out or transfers yet.",
  },
  {
    value: "sip_trunk",
    label: "Provider SIP trunk",
    hint: "A number from Plivo, Telnyx, Twilio, Exotel or Vobiz. Point its SIP origination at your LiveKit SIP URI; add the termination host to call out.",
  },
];

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      {children}
      {hint && <span className="text-[11px] text-slate-400">{hint}</span>}
    </label>
  );
}

export function AddNumberForm({
  agents,
  onAdd,
}: {
  agents: Agent[];
  onAdd: (body: PhoneNumberCreate) => Promise<boolean>;
}) {
  const [number, setNumber] = useState("");
  const [label, setLabel] = useState("");
  const [provider, setProvider] = useState<PhoneProvider>("sip_trunk");
  const [agentId, setAgentId] = useState("");
  const [address, setAddress] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [adding, setAdding] = useState(false);
  const canCallOut = provider === "sip_trunk";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAdding(true);
    const added = await onAdd({
      number: number.trim(),
      label: label.trim(),
      provider,
      agent_id: agentId || null,
      outbound:
        canCallOut && address.trim()
          ? { address: address.trim(), username: username.trim(), password }
          : null,
    });
    setAdding(false);
    if (added) {
      setNumber("");
      setLabel("");
      setAddress("");
      setUsername("");
      setPassword("");
    }
  }

  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-4 p-4">
        <h2 className="text-[13px] font-semibold">Add a number</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <Field label="Number" hint="International format">
            <input
              className={INPUT}
              value={number}
              placeholder="+14155550100"
              onChange={(e) => setNumber(e.target.value)}
            />
          </Field>
          <Field label="Label">
            <input
              className={INPUT}
              value={label}
              placeholder="Front desk"
              onChange={(e) => setLabel(e.target.value)}
            />
          </Field>
          <Field label="Where it comes from">
            <select
              className={INPUT}
              value={provider}
              onChange={(e) => setProvider(e.target.value as PhoneProvider)}
            >
              {PROVIDERS.map((choice) => (
                <option key={choice.value} value={choice.value}>
                  {choice.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Answered by">
            <select className={INPUT} value={agentId} onChange={(e) => setAgentId(e.target.value)}>
              <option value="">No agent yet</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <p className="text-[11px] text-slate-500">
          {PROVIDERS.find((choice) => choice.value === provider)?.hint}
        </p>
        {canCallOut && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Field label="Outbound SIP host (optional)" hint="Needed for “Call me” and campaigns">
              <input
                className={INPUT}
                value={address}
                placeholder="example.pstn.twilio.com"
                onChange={(e) => setAddress(e.target.value)}
              />
            </Field>
            <Field label="SIP username">
              <input
                className={INPUT}
                value={username}
                autoComplete="off"
                onChange={(e) => setUsername(e.target.value)}
              />
            </Field>
            <Field label="SIP password" hint="Sent to LiveKit only; not stored here">
              <input
                className={INPUT}
                type="password"
                value={password}
                autoComplete="new-password"
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
          </div>
        )}
        <div className="flex justify-end">
          <Button type="submit" variant="primary" disabled={adding || !number.trim()}>
            {adding ? "Adding…" : "Add number"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

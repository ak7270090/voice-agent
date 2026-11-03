"use client";

import { PhoneOutgoing } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

import { Button, Card } from "@/components/ui/primitives";
import { listPhoneNumbers, type PhoneNumber, startPhoneCall } from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-slate-200 px-3 py-1.5 text-[13px] outline-none focus:border-brand-500";

/** Rings a real phone with this agent's published flow, from a number that can call out. */
export function CallMe({ agentId, onCallStarted }: { agentId: string; onCallStarted: () => void }) {
  const [numbers, setNumbers] = useState<PhoneNumber[]>([]);
  const [fromId, setFromId] = useState("");
  const [toNumber, setToNumber] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [calling, setCalling] = useState(false);

  useEffect(() => {
    listPhoneNumbers()
      .then((all) => {
        const outbound = all.filter((number) => number.can_call_out);
        setNumbers(outbound);
        setFromId(outbound[0]?.id ?? "");
      })
      .catch(() => undefined);
  }, []);

  async function call(event: FormEvent) {
    event.preventDefault();
    setCalling(true);
    try {
      await startPhoneCall(agentId, toNumber.trim(), fromId);
      setStatus(`Ringing ${toNumber.trim()}…`);
      onCallStarted();
    } catch (cause) {
      setStatus(`Could not call: ${(cause as Error).message}`);
    } finally {
      setCalling(false);
    }
  }

  return (
    <Card>
      <form onSubmit={call} className="flex flex-col gap-3 p-4">
        <h3 className="flex items-center gap-2 text-[13px] font-semibold">
          <PhoneOutgoing size={14} /> Call me
        </h3>
        {numbers.length === 0 ? (
          <p className="text-[13px] text-slate-400">
            Needs a number with an outbound trunk.{" "}
            <Link href="/numbers" className="text-brand-600 hover:underline">
              Add one
            </Link>
            .
          </p>
        ) : (
          <>
            <input
              className={INPUT}
              value={toNumber}
              placeholder="Your phone, e.g. +919876543210"
              onChange={(e) => setToNumber(e.target.value)}
            />
            <select className={INPUT} value={fromId} onChange={(e) => setFromId(e.target.value)}>
              {numbers.map((number) => (
                <option key={number.id} value={number.id}>
                  From {number.number} {number.label && `(${number.label})`}
                </option>
              ))}
            </select>
            <Button type="submit" variant="primary" disabled={calling || !toNumber.trim()}>
              {calling ? "Calling…" : "Ring my phone"}
            </Button>
            <p className="text-[11px] text-slate-400">
              Runs the published flow. Voicemail gets the agent&apos;s voicemail message.
            </p>
          </>
        )}
        {status && <p className="text-[13px] text-slate-600">{status}</p>}
      </form>
    </Card>
  );
}

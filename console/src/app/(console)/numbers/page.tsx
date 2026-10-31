"use client";

import { useEffect, useState } from "react";

import { AddNumberForm } from "@/components/numbers/AddNumberForm";
import { NumberList } from "@/components/numbers/NumberList";
import { PageHeader } from "@/components/ui/primitives";
import {
  type Agent,
  addPhoneNumber,
  deletePhoneNumber,
  listAgents,
  listPhoneNumbers,
  type PhoneNumber,
  type PhoneNumberCreate,
  updatePhoneNumber,
} from "@/lib/api";

export default function NumbersPage() {
  const [numbers, setNumbers] = useState<PhoneNumber[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPhoneNumbers()
      .then(setNumbers)
      .catch((cause: Error) => setError(cause.message));
    listAgents()
      .then(setAgents)
      .catch(() => undefined);
  }, []);

  async function add(body: PhoneNumberCreate): Promise<boolean> {
    try {
      const added = await addPhoneNumber(body);
      setNumbers((current) => [...current, added]);
      setError(null);
      return true;
    } catch (cause) {
      setError(`Could not add ${body.number}: ${(cause as Error).message}`);
      return false;
    }
  }

  async function bind(numberId: string, agentId: string | null) {
    try {
      const updated = await updatePhoneNumber(numberId, { agent_id: agentId });
      setNumbers((current) => current.map((n) => (n.id === numberId ? updated : n)));
    } catch (cause) {
      setError((cause as Error).message);
    }
  }

  async function remove(numberId: string) {
    try {
      await deletePhoneNumber(numberId);
      setNumbers((current) => current.filter((n) => n.id !== numberId));
    } catch (cause) {
      setError((cause as Error).message);
    }
  }

  return (
    <>
      <PageHeader>
        <span className="font-semibold">Phone numbers</span>
      </PageHeader>
      <div className="flex flex-col gap-5 p-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Phone numbers</h1>
          <p className="mt-1 text-[13px] text-slate-500">
            Each number is answered by one agent&apos;s published flow. Moving a number to another
            agent takes effect on the next call.
          </p>
        </div>
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}
        <AddNumberForm agents={agents} onAdd={add} />
        <NumberList numbers={numbers} agents={agents} onBind={bind} onDelete={remove} />
      </div>
    </>
  );
}

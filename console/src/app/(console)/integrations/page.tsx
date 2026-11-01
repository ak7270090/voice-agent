"use client";

import { useEffect, useState } from "react";

import { IntegrationGuide } from "@/components/integrations/IntegrationGuide";
import { SecretsCard } from "@/components/integrations/SecretsCard";
import { PageHeader } from "@/components/ui/primitives";
import { deleteSecret, listSecrets, saveSecret, type Secret } from "@/lib/api";

export default function IntegrationsPage() {
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSecrets()
      .then(setSecrets)
      .catch((cause: Error) => setError(cause.message));
  }, []);

  async function save(name: string, value: string): Promise<boolean> {
    try {
      const saved = await saveSecret(name, value);
      setSecrets((current) =>
        [...current.filter((secret) => secret.name !== name), saved].sort((a, b) =>
          a.name.localeCompare(b.name),
        ),
      );
      setError(null);
      return true;
    } catch (cause) {
      setError(`Could not save ${name}: ${(cause as Error).message}`);
      return false;
    }
  }

  async function remove(name: string) {
    try {
      await deleteSecret(name);
      setSecrets((current) => current.filter((secret) => secret.name !== name));
    } catch (cause) {
      setError((cause as Error).message);
    }
  }

  return (
    <>
      <PageHeader>
        <span className="font-semibold">Integrations</span>
      </PageHeader>
      <div className="flex flex-col gap-5 p-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Integrations</h1>
          <p className="mt-1 text-[13px] text-slate-500">
            Agents act in other systems during the call (free times, bookings, lookups) and send
            each call&apos;s result after it. Save the keys here, then use them in a flow&apos;s
            Tool nodes or an agent&apos;s After the call actions.
          </p>
        </div>
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}
        <SecretsCard secrets={secrets} onSave={save} onDelete={remove} />
        <IntegrationGuide />
      </div>
    </>
  );
}

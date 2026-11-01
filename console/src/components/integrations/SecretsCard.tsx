"use client";

import { KeyRound, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";

import { Button, Card } from "@/components/ui/primitives";
import type { Secret } from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-[13px] outline-none focus:border-brand-500";
const NAME_PATTERN = /^[A-Z][A-Z0-9_]*$/;

/** Keys and tokens: saved by name, never shown again; tools use them as {secret.NAME}. */
export function SecretsCard({
  secrets,
  onSave,
  onDelete,
}: {
  secrets: Secret[];
  onSave: (name: string, value: string) => Promise<boolean>;
  onDelete: (name: string) => void;
}) {
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const replacing = secrets.some((secret) => secret.name === name);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await onSave(name, value)) {
      setName("");
      setValue("");
    }
  }

  return (
    <Card>
      <div className="border-b border-slate-100 px-4 py-3">
        <h2 className="text-[13px] font-semibold">Keys and tokens</h2>
        <p className="text-[11px] text-slate-400">
          Stored encrypted. The console shows only a preview; tools send a key as{" "}
          <code className="font-mono">{"{secret.NAME}"}</code>, and it never reaches the LLM, the
          transcript or the traces.
        </p>
      </div>
      {secrets.length === 0 ? (
        <p className="px-4 py-3 text-[13px] text-slate-400">No keys saved yet.</p>
      ) : (
        <table className="w-full text-[13px]">
          <tbody>
            {secrets.map((secret) => (
              <tr key={secret.name} className="border-b border-slate-100">
                <td className="px-4 py-2 font-mono text-xs">{secret.name}</td>
                <td className="px-4 py-2 font-mono text-xs text-slate-400">{secret.preview}</td>
                <td className="px-4 py-2 text-xs text-slate-400">
                  Updated {new Date(secret.updated_at).toLocaleString()}
                </td>
                <td className="px-4 py-2 text-right">
                  <button
                    type="button"
                    aria-label={`Delete ${secret.name}`}
                    onClick={() => onDelete(secret.name)}
                    className="text-slate-400 hover:text-red-600"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form onSubmit={submit} className="grid grid-cols-[14rem_1fr_auto] items-end gap-2 p-4">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600">Name</span>
          <input
            className={`${INPUT} font-mono text-xs`}
            value={name}
            placeholder="CALCOM_KEY"
            onChange={(e) => setName(e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, "_"))}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600">
            {replacing ? "New value (replaces the saved one)" : "Value"}
          </span>
          <input
            className={`${INPUT} font-mono text-xs`}
            type="password"
            autoComplete="off"
            value={value}
            placeholder="Paste the key, token, webhook URL or JSON key"
            onChange={(e) => setValue(e.target.value)}
          />
        </label>
        <Button type="submit" variant="primary" disabled={!NAME_PATTERN.test(name) || !value}>
          <KeyRound size={14} /> {replacing ? "Replace" : "Save"}
        </Button>
      </form>
    </Card>
  );
}

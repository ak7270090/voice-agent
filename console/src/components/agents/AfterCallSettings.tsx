"use client";

import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/primitives";
import {
  type AfterCallAction,
  type AfterCallEvent,
  type AfterCallKind,
  listSecrets,
} from "@/lib/api";

const INPUT =
  "w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-[13px] outline-none focus:border-brand-500";

const KINDS: Record<AfterCallKind, { label: string; secretLabel: string; suggested: string }> = {
  webhook: {
    label: "Webhook",
    secretLabel: "Signing secret (optional)",
    suggested: "WEBHOOK_SECRET",
  },
  slack: { label: "Slack", secretLabel: "Incoming webhook URL", suggested: "SLACK_WEBHOOK" },
  hubspot: { label: "HubSpot", secretLabel: "Private app token", suggested: "HUBSPOT_TOKEN" },
  google_sheets: {
    label: "Google Sheets",
    secretLabel: "Service account JSON key",
    suggested: "GOOGLE_KEY",
  },
};
const EVENTS: { value: AfterCallEvent; label: string }[] = [
  { value: "call.analysed", label: "After the analysis (with summary)" },
  { value: "call.ended", label: "As soon as the call ends" },
];

function newAction(kind: AfterCallKind): AfterCallAction {
  return {
    // Made here, not by the API, so saving the agent again keeps each action's deliveries.
    id: crypto.randomUUID().slice(0, 8),
    kind,
    event: kind === "webhook" ? "call.ended" : "call.analysed",
    enabled: true,
    url: "",
    secret: kind === "webhook" ? "" : KINDS[kind].suggested,
    spreadsheet_id: "",
    sheet_name: "Sheet1",
  };
}

/** Where each call's result goes once it ends: webhooks, Slack, HubSpot, Google Sheets. */
export function AfterCallSettings({
  actions,
  onChange,
}: {
  actions: AfterCallAction[];
  onChange: (actions: AfterCallAction[]) => void;
}) {
  const [secretNames, setSecretNames] = useState<string[]>([]);

  useEffect(() => {
    listSecrets()
      .then((secrets) => setSecretNames(secrets.map((secret) => secret.name)))
      .catch(() => undefined);
  }, []);

  const update = (index: number, changes: Partial<AfterCallAction>) =>
    onChange(actions.map((action, n) => (n === index ? { ...action, ...changes } : action)));

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-200 p-3">
      <div>
        <h3 className="text-xs font-semibold text-slate-700">After the call</h3>
        <p className="text-[11px] text-slate-400">
          Sends every call&apos;s result; a receiver that is down is retried (10 s, 30 s, 90 s…).
          Keys are saved on the Integrations page.
        </p>
      </div>
      {actions.map((action, index) => {
        const kind = KINDS[action.kind];
        const missing = action.secret !== "" && !secretNames.includes(action.secret);
        return (
          <div
            key={action.id ?? index}
            className="flex flex-col gap-2 rounded-lg border border-slate-100 bg-slate-50/60 p-2.5"
          >
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 text-[13px] font-medium">
                <input
                  type="checkbox"
                  checked={action.enabled}
                  onChange={(e) => update(index, { enabled: e.target.checked })}
                />
                {kind.label}
              </label>
              <select
                className={`${INPUT} ml-auto w-64`}
                value={action.event}
                onChange={(e) => update(index, { event: e.target.value as AfterCallEvent })}
              >
                {EVENTS.map((event) => (
                  <option key={event.value} value={event.value}>
                    {event.label}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                variant="danger"
                aria-label={`Remove ${kind.label}`}
                onClick={() => onChange(actions.filter((_, n) => n !== index))}
              >
                <Trash2 size={14} />
              </Button>
            </div>
            <div className="grid grid-cols-2 items-start gap-2">
              {action.kind === "webhook" && (
                <input
                  className={INPUT}
                  value={action.url}
                  placeholder="https://n8n.example.com/webhook/calls"
                  onChange={(e) => update(index, { url: e.target.value })}
                />
              )}
              {action.kind === "google_sheets" && (
                <input
                  className={INPUT}
                  value={action.spreadsheet_id}
                  placeholder="Spreadsheet ID (from its link)"
                  onChange={(e) => update(index, { spreadsheet_id: e.target.value })}
                />
              )}
              <label className="flex flex-col gap-1">
                <select
                  className={INPUT}
                  value={action.secret}
                  onChange={(e) => update(index, { secret: e.target.value })}
                >
                  {[...new Set(["", action.secret, ...secretNames])].map((name) => (
                    <option key={name} value={name}>
                      {name || `${kind.secretLabel}: none`}
                    </option>
                  ))}
                </select>
                <span className={`text-[11px] ${missing ? "text-red-600" : "text-slate-400"}`}>
                  {missing ? `${action.secret} is not saved yet` : kind.secretLabel}
                </span>
              </label>
              {action.kind === "google_sheets" && (
                <input
                  className={INPUT}
                  value={action.sheet_name}
                  placeholder="Tab name, e.g. Sheet1"
                  onChange={(e) => update(index, { sheet_name: e.target.value })}
                />
              )}
            </div>
          </div>
        );
      })}
      <div className="flex flex-wrap gap-2">
        {(Object.keys(KINDS) as AfterCallKind[]).map((kind) => (
          <Button key={kind} type="button" onClick={() => onChange([...actions, newAction(kind)])}>
            <Plus size={14} /> {KINDS[kind].label}
          </Button>
        ))}
      </div>
    </div>
  );
}

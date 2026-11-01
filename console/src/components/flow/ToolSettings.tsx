"use client";

import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import {
  type CalcomResource,
  type CalcomSettings,
  type FlowNodeData,
  listSecrets,
  type ToolKind,
} from "@/lib/api";

import { INPUT, JsonEditor, KeyValueEditor, Labelled, ListInput } from "./fields";

const KINDS: { value: ToolKind; label: string }[] = [
  { value: "http", label: "HTTP request (any API)" },
  { value: "calcom_availability", label: "Cal.com: free times" },
  { value: "calcom_booking", label: "Cal.com: book" },
];

export const DEFAULT_CALCOM: CalcomSettings = {
  api_key_secret: "CALCOM_KEY",
  time_zone: "Asia/Kolkata",
  resources: [],
  resource_field: "doctor",
  name_field: "patient_name",
  attendee_email: "",
  api_url: "https://api.cal.com/v2",
};

type Props = {
  nodeId: string;
  data: FlowNodeData;
  set: (changes: Partial<FlowNodeData>) => void;
};

export function ToolSettings({ nodeId, data, set }: Props) {
  const kind = data.kind ?? "http";
  const [secretNames, setSecretNames] = useState<string[]>([]);

  useEffect(() => {
    listSecrets()
      .then((secrets) => setSecretNames(secrets.map((secret) => secret.name)))
      .catch(() => undefined);
  }, []);

  return (
    <>
      <Labelled label="Kind">
        <select
          className={INPUT}
          value={kind}
          onChange={(e) => {
            const next = e.target.value as ToolKind;
            set({ kind: next, calcom: next === "http" ? null : (data.calcom ?? DEFAULT_CALCOM) });
          }}
        >
          {KINDS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </Labelled>
      <Labelled label="Function name" hint="lowercase_with_underscores; the LLM sees this">
        <input
          className={INPUT}
          value={data.name ?? ""}
          onChange={(e) => set({ name: e.target.value })}
        />
      </Labelled>
      <Labelled label="Description" hint="When to use it and what it returns">
        <input
          className={INPUT}
          value={data.description ?? ""}
          onChange={(e) => set({ description: e.target.value })}
        />
      </Labelled>

      {kind === "http" ? (
        <HttpRequest key={nodeId} data={data} set={set} />
      ) : (
        <Calcom
          key={nodeId}
          booking={kind === "calcom_booking"}
          settings={data.calcom ?? DEFAULT_CALCOM}
          secretNames={secretNames}
          onChange={(calcom) => set({ calcom })}
        />
      )}

      <Labelled
        label="Say while it runs (optional)"
        hint="Spoken only if the call takes more than a moment"
      >
        <input
          className={INPUT}
          value={data.say_while_running ?? ""}
          placeholder="e.g. One moment, let me check."
          onChange={(e) => set({ say_while_running: e.target.value })}
        />
      </Labelled>
      <KeyValueEditor
        label="Save to fields (field ← path in the JSON result)"
        rows={data.save_to_fields ?? {}}
        onChange={(save_to_fields) => set({ save_to_fields })}
      />
      <Labelled
        label="Show the LLM only (optional)"
        hint="Paths in the JSON result, comma-separated; empty shows all of it"
      >
        <ListInput
          key={nodeId}
          values={data.result_fields ?? []}
          placeholder="e.g. doctor, free_times"
          onChange={(result_fields) => set({ result_fields })}
        />
      </Labelled>
    </>
  );
}

function HttpRequest({ data, set }: Omit<Props, "nodeId">) {
  return (
    <>
      <div className="grid grid-cols-[90px_1fr] gap-2">
        <Labelled label="Method">
          <select
            className={INPUT}
            value={data.method ?? "GET"}
            onChange={(e) => set({ method: e.target.value as "GET" | "POST" })}
          >
            <option>GET</option>
            <option>POST</option>
          </select>
        </Labelled>
        <Labelled
          label="URL"
          hint="{field} from collected fields; {caller_number} is the number on the other end"
        >
          <input
            className={INPUT}
            value={data.url ?? ""}
            onChange={(e) => set({ url: e.target.value })}
          />
        </Labelled>
      </div>
      <KeyValueEditor
        label="Headers ({secret.NAME} for a saved key)"
        rows={data.headers ?? {}}
        keyPlaceholder="Authorization"
        valuePlaceholder="Bearer {secret.CRM_TOKEN}"
        onChange={(headers) => set({ headers })}
      />
      {data.method === "POST" && (
        <JsonEditor
          label="JSON body"
          hint={'Nested JSON; "{field}" alone keeps the field\'s type (an age stays a number)'}
          value={data.body ?? {}}
          onChange={(body) => set({ body })}
        />
      )}
    </>
  );
}

function Calcom({
  booking,
  settings,
  secretNames,
  onChange,
}: {
  booking: boolean;
  settings: CalcomSettings;
  secretNames: string[];
  onChange: (settings: CalcomSettings) => void;
}) {
  const set = (changes: Partial<CalcomSettings>) => onChange({ ...settings, ...changes });
  const setResource = (index: number, changes: Partial<CalcomResource>) =>
    set({
      resources: settings.resources.map((resource, n) =>
        n === index ? { ...resource, ...changes } : resource,
      ),
    });
  const missingSecret =
    settings.api_key_secret !== "" && !secretNames.includes(settings.api_key_secret);

  return (
    <>
      <Labelled
        label="Cal.com API key"
        hint={
          missingSecret
            ? `${settings.api_key_secret} is not saved yet: add it on the Integrations page`
            : "A key saved on the Integrations page"
        }
      >
        <select
          className={INPUT}
          value={settings.api_key_secret}
          onChange={(e) => set({ api_key_secret: e.target.value })}
        >
          {[...new Set(["", settings.api_key_secret, ...secretNames])].map((name) => (
            <option key={name} value={name}>
              {name || "Choose a saved key"}
            </option>
          ))}
        </select>
      </Labelled>
      <div className="grid grid-cols-2 gap-2">
        <Labelled label="Time zone">
          <input
            className={INPUT}
            value={settings.time_zone}
            onChange={(e) => set({ time_zone: e.target.value })}
          />
        </Labelled>
        <Labelled label="Field naming who" hint="e.g. doctor, stylist">
          <input
            className={`${INPUT} font-mono text-xs`}
            value={settings.resource_field}
            onChange={(e) => set({ resource_field: e.target.value })}
          />
        </Labelled>
      </div>
      {booking && (
        <div className="grid grid-cols-2 gap-2">
          <Labelled label="Field with the person's name">
            <input
              className={`${INPUT} font-mono text-xs`}
              value={settings.name_field}
              onChange={(e) => set({ name_field: e.target.value })}
            />
          </Labelled>
          <Labelled label="Attendee email" hint="Empty: the Cal.com account's own email">
            <input
              className={INPUT}
              value={settings.attendee_email}
              onChange={(e) => set({ attendee_email: e.target.value })}
            />
          </Labelled>
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-slate-600">
          Who can be booked: name, Cal.com event type ID, words callers use
        </span>
        {settings.resources.map((resource, index) => (
          <div key={index} className="flex flex-col gap-1 rounded-lg border border-slate-200 p-2">
            <div className="flex gap-1.5">
              <input
                className={INPUT}
                value={resource.name}
                placeholder="Dr. Priya Mehta"
                onChange={(e) => setResource(index, { name: e.target.value })}
              />
              <input
                className={`${INPUT} w-28 font-mono text-xs`}
                value={resource.event_type_id ?? ""}
                placeholder="Event type ID"
                inputMode="numeric"
                onChange={(e) => {
                  const digits = e.target.value.replace(/\D/g, "");
                  setResource(index, { event_type_id: digits ? Number(digits) : null });
                }}
              />
              <button
                type="button"
                aria-label={`Remove ${resource.name || "entry"}`}
                onClick={() => set({ resources: settings.resources.filter((_, n) => n !== index) })}
                className="text-slate-400 hover:text-red-600"
              >
                <Trash2 size={13} />
              </button>
            </div>
            <ListInput
              values={resource.keywords}
              placeholder="Words callers use, e.g. skin, rash"
              onChange={(keywords) => setResource(index, { keywords })}
            />
          </div>
        ))}
        <button
          type="button"
          onClick={() =>
            set({
              resources: [...settings.resources, { name: "", event_type_id: null, keywords: [] }],
            })
          }
          className="flex items-center gap-1 self-start text-xs font-medium text-brand-700"
        >
          <Plus size={13} /> Add
        </button>
      </div>
      <p className="text-[11px] text-slate-400">
        {booking
          ? `Reads ${settings.resource_field}, day, time and ${settings.name_field}; answers booking_id, weekday and time.`
          : `Reads ${settings.resource_field} and day; answers free_times and next_open_days.`}
      </p>
    </>
  );
}

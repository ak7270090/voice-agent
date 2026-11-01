"use client";

import { RotateCw } from "lucide-react";
import { useEffect, useState } from "react";

import { Button, Card, Chip } from "@/components/ui/primitives";
import {
  type AfterCallKind,
  type Delivery,
  type DeliveryStatus,
  listDeliveries,
  retryDelivery,
} from "@/lib/api";

// While a delivery waits for its next attempt, look again this often.
const POLL_MS = 5000;
const KIND_LABELS: Record<AfterCallKind, string> = {
  webhook: "Webhook",
  slack: "Slack",
  hubspot: "HubSpot",
  google_sheets: "Google Sheets",
};
const STATUS_TONES: Record<DeliveryStatus, "neutral" | "green" | "amber" | "red"> = {
  pending: "amber",
  sent: "green",
  skipped: "neutral",
  failed: "red",
};

/** The call's after-call actions: what was sent where, retries, and "send again". */
export function Deliveries({ callId }: { callId: string }) {
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [error, setError] = useState<string | null>(null);

  const pending = deliveries.some((delivery) => delivery.status === "pending");
  useEffect(() => {
    const load = () =>
      listDeliveries(callId)
        .then(setDeliveries)
        .catch((cause: Error) => setError(cause.message));
    load();
    if (!pending) return;
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [callId, pending]);

  async function sendAgain(deliveryId: string) {
    try {
      const reset = await retryDelivery(callId, deliveryId);
      setDeliveries((current) => current.map((d) => (d.id === deliveryId ? reset : d)));
    } catch (cause) {
      setError((cause as Error).message);
    }
  }

  return (
    <Card>
      <h2 className="border-b border-slate-100 px-4 py-3 text-[13px] font-semibold">
        Sent after the call
      </h2>
      <div className="flex flex-col gap-2 p-4 text-xs">
        {error && <p className="text-red-600">{error}</p>}
        {deliveries.length === 0 && (
          <p className="text-slate-400">No after-call actions for this agent.</p>
        )}
        {deliveries.map((delivery) => (
          <div key={delivery.id} className="flex flex-col gap-1 border-b border-slate-100 pb-2">
            <div className="flex items-center gap-2">
              <span className="font-medium">{KIND_LABELS[delivery.kind]}</span>
              <span className="text-slate-400">{delivery.event}</span>
              <span className="ml-auto">
                <Chip tone={STATUS_TONES[delivery.status]}>{delivery.status}</Chip>
              </span>
            </div>
            <div className="flex items-center gap-2 text-slate-500">
              <span>
                {delivery.attempts} attempt{delivery.attempts === 1 ? "" : "s"}
                {delivery.response_status !== null && ` · HTTP ${delivery.response_status}`}
              </span>
              {(delivery.status === "failed" || delivery.status === "skipped") && (
                <Button type="button" className="ml-auto" onClick={() => sendAgain(delivery.id)}>
                  <RotateCw size={12} /> Send again
                </Button>
              )}
            </div>
            {delivery.last_error && (
              <code className="break-all text-[11px] text-slate-500">{delivery.last_error}</code>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

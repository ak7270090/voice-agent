"use client";

import { Button, Card, Chip } from "@/components/ui/primitives";
import type { Agent, PhoneNumber } from "@/lib/api";
import { DEMO_MODE } from "@/lib/demo";

const SELECT =
  "rounded-lg border border-slate-200 px-2 py-1 text-[13px] outline-none focus:border-brand-500";

export function NumberList({
  numbers,
  agents,
  onBind,
  onDelete,
}: {
  numbers: PhoneNumber[];
  agents: Agent[];
  onBind: (numberId: string, agentId: string | null) => void;
  onDelete: (numberId: string) => void;
}) {
  return (
    <Card>
      <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
        <h2 className="text-[13px] font-semibold">Numbers</h2>
        <Chip>{numbers.length}</Chip>
      </div>
      {numbers.length === 0 ? (
        <p className="px-4 py-3 text-[13px] text-slate-400">No numbers yet. Add one above.</p>
      ) : (
        <table className="w-full text-[13px]">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="px-4 py-2 font-medium">Number</th>
              <th className="px-4 py-2 font-medium">Answered by</th>
              <th className="px-4 py-2 font-medium">Can</th>
              {!DEMO_MODE && <th className="px-4 py-2 font-medium">LiveKit dispatch rule</th>}
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {numbers.map((number) => (
              <tr key={number.id} className="border-t border-slate-100 align-top text-slate-700">
                <td className="px-4 py-2">
                  <div className="font-medium tabular-nums">{number.number}</div>
                  <div className="text-xs text-slate-400">
                    {number.label || (number.provider === "livekit" ? "LiveKit" : "SIP trunk")}
                  </div>
                </td>
                <td className="px-4 py-2">
                  <select
                    className={SELECT}
                    value={number.agent_id ?? ""}
                    onChange={(e) => onBind(number.id, e.target.value || null)}
                  >
                    <option value="">Nobody (calls go unanswered)</option>
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-2">
                  <div className="flex flex-wrap gap-1">
                    <Chip tone="green">answer</Chip>
                    {number.can_call_out && <Chip tone="brand">call out</Chip>}
                    {number.can_transfer && <Chip tone="brand">transfer</Chip>}
                  </div>
                </td>
                {!DEMO_MODE && (
                  <td className="px-4 py-2">
                    <code className="text-xs">{number.dispatch_rule_id}</code>
                    {number.provider === "livekit" && (
                      <div className="mt-1 text-[11px] text-slate-400">
                        Assign it to the number once:{" "}
                        <code>
                          lk number update --id &lt;number id&gt; --sip-dispatch-rule-id{" "}
                          {number.dispatch_rule_id}
                        </code>
                      </div>
                    )}
                  </td>
                )}
                <td className="px-4 py-2 text-right">
                  <Button variant="danger" onClick={() => onDelete(number.id)}>
                    Remove
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

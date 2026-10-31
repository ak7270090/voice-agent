import { CONTACT_STATUS_STYLES } from "@/components/campaigns/CampaignProgress";
import { Card, Chip } from "@/components/ui/primitives";
import type { CampaignContact } from "@/lib/api";

function details(contact: CampaignContact): string {
  return Object.entries(contact.variables)
    .map(([name, value]) => `${name}: ${value}`)
    .join(", ");
}

export function ContactTable({ contacts }: { contacts: CampaignContact[] }) {
  return (
    <Card>
      <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
        <h2 className="text-[13px] font-semibold">Contacts</h2>
        <Chip>{contacts.length}</Chip>
      </div>
      {contacts.length === 0 ? (
        <p className="px-4 py-3 text-[13px] text-slate-400">
          Upload a CSV with columns phone, name, consent, and any details the agent should know.
        </p>
      ) : (
        <table className="w-full text-[13px]">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="px-4 py-2 font-medium">Contact</th>
              <th className="px-4 py-2 font-medium">Details</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Outcome</th>
              <th className="px-4 py-2 text-right font-medium">Tries</th>
              <th className="px-4 py-2 font-medium">Next try</th>
            </tr>
          </thead>
          <tbody>
            {contacts.map((contact) => {
              const style = CONTACT_STATUS_STYLES[contact.status];
              return (
                <tr key={contact.id} className="border-t border-slate-100 text-slate-700">
                  <td className="px-4 py-2">
                    <div className="font-medium">{contact.name || "—"}</div>
                    <div className="text-xs tabular-nums text-slate-400">{contact.phone}</div>
                  </td>
                  <td className="px-4 py-2 text-xs text-slate-500">{details(contact) || "—"}</td>
                  <td className="px-4 py-2">
                    <Chip tone={style.tone} dot={contact.status === "calling"}>
                      {style.label}
                    </Chip>
                  </td>
                  <td className="px-4 py-2">
                    {contact.outcome ? <Chip tone="brand">{contact.outcome}</Chip> : "—"}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">{contact.attempts}</td>
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {contact.status === "retry" && contact.next_attempt_at
                      ? new Date(contact.next_attempt_at).toLocaleTimeString()
                      : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </Card>
  );
}

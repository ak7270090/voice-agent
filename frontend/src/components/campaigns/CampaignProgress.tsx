import { Chip } from "@/components/ui/primitives";
import type { Campaign, CampaignStatus, ContactStatus } from "@/lib/api";

// Order and colour of each contact status in the progress bar and the table.
export const CONTACT_STATUS_STYLES: Record<
  ContactStatus,
  { label: string; bar: string; tone: "neutral" | "brand" | "green" | "amber" | "red" }
> = {
  done: { label: "Done", bar: "bg-emerald-500", tone: "green" },
  opted_out: { label: "Opted out", bar: "bg-slate-500", tone: "neutral" },
  failed: { label: "Not reached", bar: "bg-red-400", tone: "red" },
  calling: { label: "Calling", bar: "bg-brand-500", tone: "brand" },
  retry: { label: "Retry later", bar: "bg-amber-400", tone: "amber" },
  pending: { label: "Waiting", bar: "bg-slate-200", tone: "neutral" },
  skipped: { label: "No consent", bar: "bg-slate-300", tone: "neutral" },
};

const CAMPAIGN_TONES: Record<CampaignStatus, "neutral" | "green" | "amber" | "brand"> = {
  draft: "neutral",
  running: "green",
  paused: "amber",
  completed: "brand",
};

export function CampaignStatusChip({ status }: { status: CampaignStatus }) {
  return (
    <Chip tone={CAMPAIGN_TONES[status]} dot={status === "running"}>
      {status}
    </Chip>
  );
}

export function CampaignProgress({ campaign }: { campaign: Campaign }) {
  const statuses = Object.keys(CONTACT_STATUS_STYLES) as ContactStatus[];
  const total = statuses.reduce((sum, status) => sum + (campaign.counts[status] ?? 0), 0);
  if (total === 0) return <p className="text-[13px] text-slate-400">No contacts yet.</p>;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-2.5 overflow-hidden rounded-full bg-slate-100">
        {statuses.map((status) => {
          const count = campaign.counts[status] ?? 0;
          return count ? (
            <div
              key={status}
              className={CONTACT_STATUS_STYLES[status].bar}
              style={{ width: `${(count / total) * 100}%` }}
            />
          ) : null;
        })}
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-slate-600">
        {statuses
          .filter((status) => campaign.counts[status])
          .map((status) => (
            <span key={status} className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${CONTACT_STATUS_STYLES[status].bar}`} />
              {CONTACT_STATUS_STYLES[status].label} {campaign.counts[status]}
            </span>
          ))}
        <span className="text-slate-400">of {total}</span>
      </div>
    </div>
  );
}

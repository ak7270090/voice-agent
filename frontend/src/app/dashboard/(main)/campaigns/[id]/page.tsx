"use client";

import { Pause, Play, Upload } from "lucide-react";
import Link from "next/link";
import { type ChangeEvent, useCallback, useEffect, useState } from "react";

import { CampaignProgress, CampaignStatusChip } from "@/components/campaigns/CampaignProgress";
import { ContactTable } from "@/components/campaigns/ContactTable";
import { Button, Card, PageHeader } from "@/components/ui/primitives";
import {
  type Campaign,
  type CampaignContact,
  type ContactImport,
  getCampaign,
  importContacts,
  listCampaignContacts,
  pauseCampaign,
  startCampaign,
} from "@/lib/api";
import { dashboardPath } from "@/lib/paths";

// The dialler places calls every few seconds; refresh as often while the campaign runs.
const REFRESH_MS = 3000;

export default function CampaignPage({ params }: { params: { id: string } }) {
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [contacts, setContacts] = useState<CampaignContact[]>([]);
  const [imported, setImported] = useState<ContactImport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    getCampaign(params.id)
      .then(setCampaign)
      .catch((cause: Error) => setError(cause.message));
    listCampaignContacts(params.id)
      .then(setContacts)
      .catch(() => undefined);
  }, [params.id]);

  useEffect(refresh, [refresh]);

  useEffect(() => {
    if (campaign?.status !== "running") return;
    const timer = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(timer);
  }, [campaign?.status, refresh]);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      setImported(await importContacts(params.id, file));
      refresh();
    } catch (cause) {
      setError(`Could not import: ${(cause as Error).message}`);
    }
  }

  async function toggle() {
    if (!campaign) return;
    try {
      const moved = await (campaign.status === "running" ? pauseCampaign : startCampaign)(
        campaign.id,
      );
      setCampaign(moved);
    } catch (cause) {
      setError((cause as Error).message);
    }
  }

  const running = campaign?.status === "running";
  return (
    <>
      <PageHeader>
        <Link href={dashboardPath("/campaigns")} className="text-slate-500 hover:text-slate-700">
          Campaigns
        </Link>
        <span className="text-slate-300">/</span>
        <span className="font-semibold">{campaign?.name ?? "…"}</span>
        {campaign && <CampaignStatusChip status={campaign.status} />}
        {campaign && campaign.status !== "completed" && (
          <span className="ml-auto flex items-center gap-2">
            <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[13px] font-medium text-slate-700 hover:bg-slate-50">
              <Upload size={14} /> Upload CSV
              <input type="file" accept=".csv,text/csv" className="hidden" onChange={upload} />
            </label>
            <Button variant="primary" onClick={toggle}>
              {running ? <Pause size={14} /> : <Play size={14} />}
              {running ? "Pause" : campaign.status === "paused" ? "Resume" : "Start"}
            </Button>
          </span>
        )}
      </PageHeader>
      <div className="flex flex-col gap-4 p-6">
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}
        {imported && (
          <p className="rounded-lg bg-emerald-50 px-3 py-2 text-[13px] text-emerald-700">
            Added {imported.added} contacts ({imported.skipped} without consent, never called).
            {imported.rejected.length > 0 &&
              ` Rejected: ${imported.rejected.map((r) => `row ${r.row} (${r.reason})`).join("; ")}.`}
          </p>
        )}
        {campaign && (
          <Card className="flex flex-col gap-3 p-4">
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
              <span>
                Calls {campaign.window_start.slice(0, 5)}–{campaign.window_end.slice(0, 5)}{" "}
                {campaign.timezone}
              </span>
              <span>Up to {campaign.max_concurrent} at once</span>
              <span>
                {campaign.max_attempts} tries, {campaign.retry_after_minutes} min apart
              </span>
            </div>
            <CampaignProgress campaign={campaign} />
          </Card>
        )}
        <ContactTable contacts={contacts} />
      </div>
    </>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CampaignForm } from "@/components/campaigns/CampaignForm";
import { CampaignProgress, CampaignStatusChip } from "@/components/campaigns/CampaignProgress";
import { Card, PageHeader } from "@/components/ui/primitives";
import {
  type Agent,
  type Campaign,
  type CampaignSettings,
  createCampaign,
  listAgents,
  listCampaigns,
  listPhoneNumbers,
  type PhoneNumber,
} from "@/lib/api";
import { dashboardPath } from "@/lib/navigation";

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [numbers, setNumbers] = useState<PhoneNumber[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCampaigns()
      .then(setCampaigns)
      .catch((cause: Error) => setError(cause.message));
    listAgents()
      .then(setAgents)
      .catch(() => setAgents([]));
    listPhoneNumbers()
      .then(setNumbers)
      .catch(() => setNumbers([]));
  }, []);

  async function create(settings: CampaignSettings) {
    try {
      const campaign = await createCampaign(settings);
      router.push(dashboardPath(`/campaigns/${campaign.id}`));
    } catch (cause) {
      setError(`Could not create the campaign: ${(cause as Error).message}`);
    }
  }

  return (
    <>
      <PageHeader>
        <span className="font-semibold">Campaigns</span>
      </PageHeader>
      <div className="flex flex-col gap-5 p-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Campaigns</h1>
          <p className="mt-1 text-[13px] text-slate-500">
            Call a list of consenting contacts with one agent, inside a daily calling window,
            retrying anyone who did not answer.
          </p>
        </div>
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-600">{error}</p>
        )}
        {agents && numbers && <CampaignForm agents={agents} numbers={numbers} onCreate={create} />}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {campaigns.map((campaign) => (
            <Link key={campaign.id} href={dashboardPath(`/campaigns/${campaign.id}`)}>
              <Card className="flex flex-col gap-3 p-4 hover:border-brand-500">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">{campaign.name}</span>
                  <CampaignStatusChip status={campaign.status} />
                  <span className="ml-auto text-xs text-slate-400">
                    {campaign.window_start.slice(0, 5)}–{campaign.window_end.slice(0, 5)}{" "}
                    {campaign.timezone}
                  </span>
                </div>
                <CampaignProgress campaign={campaign} />
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}

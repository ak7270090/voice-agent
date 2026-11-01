import { Card } from "@/components/ui/primitives";

type Integration = {
  name: string;
  when: "During the call" | "After the call";
  secret: string;
  steps: string;
};

const INTEGRATIONS: Integration[] = [
  {
    name: "Cal.com",
    when: "During the call",
    secret: "CALCOM_KEY: Settings, Developer, API keys in Cal.com",
    steps:
      "Give each doctor an event type with their hours. Create an agent from the Clinic booking (Cal.com) template and set each doctor's event type ID (the number in its Cal.com link).",
  },
  {
    name: "Any API",
    when: "During the call",
    secret: "Any name, e.g. CRM_TOKEN",
    steps:
      "Add a Tool node, set its URL and headers, e.g. Authorization: Bearer {secret.CRM_TOKEN}. {caller_number} finds a returning caller in a CRM.",
  },
  {
    name: "Webhook (n8n, Zapier, Make)",
    when: "After the call",
    secret: "Optional signing secret, e.g. WEBHOOK_SECRET",
    steps:
      'Add a webhook under the agent\'s After the call. Requests carry X-Studio-Signature: sha256 HMAC of "<X-Studio-Timestamp>.<body>" with the secret.',
  },
  {
    name: "Slack",
    when: "After the call",
    secret: "SLACK_WEBHOOK: an incoming webhook URL from api.slack.com/apps",
    steps: "Posts who called, how it ended, the summary and a link to the call.",
  },
  {
    name: "HubSpot",
    when: "After the call",
    secret: "HUBSPOT_TOKEN: a private app token with contacts and notes scopes",
    steps:
      "Finds the contact by phone number (creates one if new) and adds the call summary as a note.",
  },
  {
    name: "Google Sheets",
    when: "After the call",
    secret: "GOOGLE_KEY: a service account's JSON key (Sheets API on)",
    steps: "Share the sheet with the service account's email as an editor; each call adds a row.",
  },
];

export function IntegrationGuide() {
  return (
    <Card>
      <h2 className="border-b border-slate-100 px-4 py-3 text-[13px] font-semibold">
        What you can connect
      </h2>
      <div className="grid grid-cols-1 gap-px bg-slate-100 md:grid-cols-2 xl:grid-cols-3">
        {INTEGRATIONS.map((integration) => (
          <div key={integration.name} className="flex flex-col gap-1.5 bg-white p-4">
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-semibold">{integration.name}</span>
              <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[10.5px] text-slate-500">
                {integration.when}
              </span>
            </div>
            <p className="font-mono text-[11px] text-slate-500">{integration.secret}</p>
            <p className="text-xs leading-relaxed text-slate-600">{integration.steps}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

import type { Metadata } from "next";

import "./website.css";

export const metadata: Metadata = {
  title: "Voice Agent Studio: AI voice agents for phone calls",
  description:
    "Design AI voice agents visually, connect them to your calendar and CRM, put them on a phone number or a contact list, and see how every call went.",
};

export default function WebsiteLayout({ children }: { children: React.ReactNode }) {
  return children;
}

import type { Metadata } from "next";

import { DEMOS } from "@/lib/website/content";

import "./website.css";

export const metadata: Metadata = {
  title: "Voice Agent Studio: AI voice agents for phone calls",
  description:
    "Design AI voice agents visually, connect them to your calendar and CRM, put them on a phone number or a contact list, and see how every call went.",
};

export default function WebsiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* The first video's poster, so the player never sits empty while it loads. */}
      <link rel="preload" as="image" type="image/webp" href={DEMOS[0].poster} />
      {children}
    </>
  );
}

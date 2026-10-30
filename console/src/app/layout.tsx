import type { Metadata } from "next";

import { Sidebar } from "@/components/shell/Sidebar";

import "./globals.css";

export const metadata: Metadata = {
  title: "Voice Agent Studio",
  description: "Build, test and run voice agents for phone and browser",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen">
        <Sidebar />
        <main className="flex min-w-0 flex-1 flex-col">{children}</main>
      </body>
    </html>
  );
}

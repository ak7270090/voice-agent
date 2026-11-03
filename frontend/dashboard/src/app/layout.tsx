import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Voice Agent Studio",
  description: "Build, test and run voice agents for phone and browser",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

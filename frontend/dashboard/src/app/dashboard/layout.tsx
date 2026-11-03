import { DemoBanner } from "@/components/shell/DemoBanner";

import "./globals.css";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <DemoBanner />
      {children}
    </div>
  );
}

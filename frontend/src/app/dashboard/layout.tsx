import { DemoBanner } from "@/components/shell/DemoBanner";
import { LargerScreenNotice } from "@/components/shell/LargerScreenNotice";

import "./globals.css";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <LargerScreenNotice />
      <div className="hidden lg:block">
        <DemoBanner />
        {children}
      </div>
    </div>
  );
}

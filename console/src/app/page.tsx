import { ServiceStatus } from "@/components/shell/ServiceStatus";

export default function OverviewPage() {
  return (
    <>
      <header className="flex h-14 items-center border-b border-slate-200 bg-white px-6 text-[13px] font-semibold">
        Overview
      </header>
      <div className="flex flex-col gap-4 p-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Voice Agent Studio</h1>
          <p className="mt-1 text-[13px] text-slate-500">
            Agents, calls and campaigns appear here as they are built.
          </p>
        </div>
        <div className="max-w-md">
          <ServiceStatus />
        </div>
      </div>
    </>
  );
}

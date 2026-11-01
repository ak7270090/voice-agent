import Link from "next/link";

import { CallTable } from "@/components/calls/CallTable";
import { Card, Chip } from "@/components/ui/primitives";
import type { Call } from "@/lib/api";

export function RecentCalls({ calls, agentId }: { calls: Call[]; agentId: string }) {
  return (
    <Card>
      <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
        <h3 className="text-[13px] font-semibold">Recent calls</h3>
        <Chip>{calls.length}</Chip>
        <Link
          href={`/calls?agent_id=${agentId}`}
          className="ml-auto text-xs text-brand-600 hover:underline"
        >
          All calls
        </Link>
      </div>
      <CallTable calls={calls} />
    </Card>
  );
}

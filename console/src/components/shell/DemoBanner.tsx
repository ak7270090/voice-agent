import { DEMO_MODE, PROJECT_URL, REPOSITORY_URL } from "@/lib/demo";

/** Shown on every page of the read-only demo build. */
export function DemoBanner() {
  if (!DEMO_MODE) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 bg-slate-900 px-6 py-2 text-[12.5px] text-slate-200">
      <span>
        <span className="mr-2 rounded bg-brand-600 px-1.5 py-0.5 text-[11px] font-semibold text-white">
          Read-only demo
        </span>
        Real agents, flows, calls and campaigns from test runs. Nothing can be changed and no calls
        are placed.
      </span>
      <span className="ml-auto flex gap-4">
        {PROJECT_URL && (
          <a href={PROJECT_URL} className="text-white underline-offset-2 hover:underline">
            Watch the videos
          </a>
        )}
        {REPOSITORY_URL && (
          <a href={REPOSITORY_URL} className="text-white underline-offset-2 hover:underline">
            Source code
          </a>
        )}
      </span>
    </div>
  );
}

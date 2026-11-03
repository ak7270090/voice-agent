import { DEMO_MODE, WEBSITE_PATH, REPOSITORY_URL } from "@/lib/demo";

/** Shown on every page of the read-only demo build. */
export function DemoBanner() {
  if (!DEMO_MODE) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 bg-slate-900 px-6 py-2 text-[12.5px] text-slate-200">
      <span>
        <span className="mr-2 rounded bg-brand-600 px-1.5 py-0.5 text-[11px] font-semibold text-white">
          Demo workspace
        </span>
        Sample agents, calls and campaigns. Changes and calls are turned off.
      </span>
      <span className="ml-auto flex gap-4">
        <a href={WEBSITE_PATH} className="text-white underline-offset-2 hover:underline">
          Back to the website
        </a>
        <a href={REPOSITORY_URL} className="text-white underline-offset-2 hover:underline">
          GitHub
        </a>
      </span>
    </div>
  );
}

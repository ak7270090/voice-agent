import { BrandMark } from "@/components/shell/BrandMark";
import { WEBSITE_DEMO_PATH } from "@/lib/demo";

/** Shown instead of the dashboard below Tailwind's `lg` width, where its layout starts to break. */
export function LargerScreenNotice() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-6 text-center lg:hidden">
      <div className="flex items-center gap-2.5 text-sm font-semibold">
        <BrandMark />
        Voice Agent Studio
      </div>
      <h1 className="mt-8 text-xl font-semibold text-slate-900">
        Open the dashboard on a larger screen
      </h1>
      <p className="mt-3 max-w-sm text-sm leading-6 text-slate-600">
        It&apos;s built for a laptop or desktop. On this screen, you can watch it in action on the
        website.
      </p>
      <a
        href={WEBSITE_DEMO_PATH}
        className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-700"
      >
        Watch the demo
      </a>
    </div>
  );
}

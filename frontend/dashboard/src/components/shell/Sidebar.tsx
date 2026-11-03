"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_SECTIONS } from "@/lib/navigation";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 shrink-0 flex-col gap-0.5 border-r border-slate-200 bg-white px-3 py-4">
      <div className="flex items-center gap-2.5 px-2 pb-5 text-sm font-semibold">
        <div className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-xs text-white">
          <svg viewBox="0 0 32 32" className="h-full w-full" aria-hidden="true">
            <path
              d="M7 13.5v5M11.5 9.5v13M16 6v20M20.5 10.5v11M25 13.5v5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.6"
              strokeLinecap="round"
            />
          </svg>
        </div>
        Voice Agent Studio
      </div>
      {NAV_SECTIONS.map((section) => (
        <div key={section.title}>
          <div className="px-2.5 pb-1.5 pt-3.5 text-[11px] uppercase tracking-wider text-slate-400">
            {section.title}
          </div>
          {section.items.map(({ label, href, icon: Icon, available }) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(`${href}/`));
            const className = clsx(
              "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px]",
              active && "bg-brand-50 font-semibold text-brand-700",
              !active && available && "text-slate-700 hover:bg-slate-50",
              !available && "cursor-default text-slate-400",
            );
            const content = (
              <>
                <Icon size={16} className={active ? "text-brand-600" : "text-slate-400"} />
                {label}
                {!available && <span className="ml-auto text-[10px] text-slate-300">soon</span>}
              </>
            );
            return available ? (
              <Link key={href} href={href} className={className}>
                {content}
              </Link>
            ) : (
              <div key={href} className={className}>
                {content}
              </div>
            );
          })}
        </div>
      ))}
    </aside>
  );
}

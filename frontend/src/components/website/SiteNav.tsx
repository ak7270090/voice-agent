"use client";

import { useEffect, useState } from "react";

import { DASHBOARD_ROOT } from "@/lib/paths";

const LINKS = [
  { id: "use-cases", label: "Use cases" },
  { id: "platform", label: "Platform" },
  { id: "integrations", label: "Integrations" },
  { id: "faq", label: "FAQ" },
];
const LOGO_WAVE = "M7 13.5v5M11.5 9.5v13M16 6v20M20.5 10.5v11M25 13.5v5";

export function SiteNav() {
  const [current, setCurrent] = useState("");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setCurrent(entry.target.id);
        });
      },
      // A section counts as current while it crosses the band just below the navigation.
      { rootMargin: "-80px 0px -60% 0px" },
    );
    LINKS.forEach(({ id }) => {
      const section = document.getElementById(id);
      if (section) observer.observe(section);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <header className="nav">
      <div className="wrap nav-inner">
        <a className="brand" href="#top">
          <span className="logo" aria-hidden="true">
            <svg viewBox="0 0 32 32">
              <path
                d={LOGO_WAVE}
                fill="none"
                stroke="currentColor"
                strokeWidth="2.6"
                strokeLinecap="round"
              />
            </svg>
          </span>
          Voice Agent Studio
        </a>
        <nav className="nav-links">
          {LINKS.map(({ id, label }) => (
            <a key={id} href={`#${id}`} className={id === current ? "current" : undefined}>
              {label}
            </a>
          ))}
        </nav>
        <div className="nav-actions">
          <a className="button primary" href={DASHBOARD_ROOT}>
            Try the demo
          </a>
        </div>
      </div>
    </header>
  );
}

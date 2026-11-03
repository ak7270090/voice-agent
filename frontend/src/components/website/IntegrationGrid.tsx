"use client";

import { type CSSProperties, useEffect, useRef } from "react";

import { APPS, type IntegrationApp } from "@/lib/website/content";

function AppIcon({ app }: { app: IntegrationApp }) {
  const outline = app.outline
    ? {
        fill: "none",
        stroke: "currentColor",
        strokeWidth: 2,
        strokeLinecap: "round" as const,
        strokeLinejoin: "round" as const,
      }
    : {};
  return (
    <svg
      className={app.wordmark ? "wordmark" : undefined}
      viewBox="0 0 24 24"
      aria-hidden="true"
      {...outline}
    >
      {app.paths.map((path) => (
        <path
          key={path.d}
          d={path.d}
          fill={app.outline ? undefined : (path.fill ?? "currentColor")}
        />
      ))}
    </svg>
  );
}

export function IntegrationGrid() {
  const grid = useRef<HTMLDivElement>(null);

  // The cards rise in one after another, once. Cards already on screen stay put.
  useEffect(() => {
    const element = grid.current;
    if (!element) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (element.getBoundingClientRect().top < innerHeight) return;
    element.classList.add("waiting");
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();
        element.classList.replace("waiting", "rising");
      },
      { threshold: 0.2 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="app-grid" ref={grid}>
      {APPS.map((app, order) => (
        <div className="app" key={app.name} style={{ "--order": order } as CSSProperties}>
          <span className="app-mark" style={{ "--mark": app.color } as CSSProperties}>
            <AppIcon app={app} />
          </span>
          <div>
            <b>{app.name}</b>
            <span>{app.text}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

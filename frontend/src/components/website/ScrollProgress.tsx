"use client";

import { useEffect, useRef } from "react";

export function ScrollProgress() {
  const bar = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const page = document.documentElement;
    let queued = false;

    function update() {
      queued = false;
      const range = page.scrollHeight - innerHeight;
      if (bar.current) bar.current.style.transform = `scaleX(${range > 0 ? scrollY / range : 0})`;
    }

    function request() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(update);
    }

    addEventListener("scroll", request, { passive: true });
    addEventListener("resize", request);
    update();
    return () => {
      removeEventListener("scroll", request);
      removeEventListener("resize", request);
    };
  }, []);

  return <div className="scroll-progress" aria-hidden="true" ref={bar} />;
}

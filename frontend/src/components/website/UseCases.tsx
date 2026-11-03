"use client";

import { useEffect, useRef, useState } from "react";

import { USE_CASES } from "@/lib/website/content";

const LINE_PAUSE_MIN_MS = 700;
const LINE_PAUSE_PER_CHAR_MS = 14;
const LINE_PAUSE_MAX_MS = 2000;
const STAGE_SCROLL_BREAKPOINT = "(max-width: 900px)";
const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

// A pause as long as the last line takes to read, so the call has a natural pace.
function pauseAfter(said: string) {
  return Math.min(LINE_PAUSE_MAX_MS, LINE_PAUSE_MIN_MS + said.length * LINE_PAUSE_PER_CHAR_MS);
}

export function UseCases() {
  const [current, setCurrent] = useState(0);
  // Bumped each time a call starts; null until the section has been reached.
  const [run, setRun] = useState<number | null>(null);
  const [shown, setShown] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const lines = useRef<HTMLOListElement>(null);
  const followingCall = useRef(true);

  const useCase = USE_CASES[current];
  const ended = shown === useCase.lines.length;

  // The first call starts when the section is reached, not while it is off screen.
  useEffect(() => {
    if (matchMedia(REDUCED_MOTION).matches) {
      setRun(0);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();
        setRun(0);
      },
      { threshold: 0.35 },
    );
    if (root.current) observer.observe(root.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (run === null) return;
    followingCall.current = true;
    const all = USE_CASES[current].lines;
    if (matchMedia(REDUCED_MOTION).matches) {
      setShown(all.length);
      return;
    }
    let timer: ReturnType<typeof setTimeout>;
    const showNext = (count: number) => {
      setShown(count);
      if (count < all.length)
        timer = setTimeout(() => showNext(count + 1), pauseAfter(all[count - 1]?.[1] ?? ""));
    };
    showNext(1);
    return () => clearTimeout(timer);
    // A new run restarts the call; `current` changes only together with it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run]);

  useEffect(() => {
    if (followingCall.current && lines.current && shown > 0) {
      lines.current.scrollTo({ top: lines.current.scrollHeight, behavior: "smooth" });
    }
  }, [shown]);

  function pick(index: number) {
    setCurrent(index);
    setShown(0);
    setRun((previous) => (previous ?? 0) + 1);
    if (lines.current) lines.current.scrollTop = 0;
    // On a phone the call sits below the list: bring it into view.
    if (matchMedia(STAGE_SCROLL_BREAKPOINT).matches) {
      stage.current?.scrollIntoView({
        block: "nearest",
        behavior: matchMedia(REDUCED_MOTION).matches ? "auto" : "smooth",
      });
    }
  }

  // Reading back up the conversation stops it jumping down to each new line.
  const stopFollowing = () => {
    followingCall.current = false;
  };

  return (
    <div className="cases" ref={root}>
      <div className="case-side">
        <div className="case-list" role="tablist">
          {USE_CASES.map((item, index) => (
            <button
              key={item.tab}
              type="button"
              role="tab"
              aria-selected={index === current}
              onClick={() => pick(index)}
            >
              <strong>{item.tab}</strong>
              <em>{item.industry}</em>
              <span>{item.text}</span>
            </button>
          ))}
        </div>
        <p className="case-note">{useCase.text}</p>
      </div>
      <div className="case-stage">
        <div className={ended ? "phone ended" : "phone"} ref={stage}>
          <div className="phone-head">
            <span className="phone-avatar" aria-hidden="true">
              {useCase.title[0]}
            </span>
            <div>
              <strong className="chat-title">{useCase.title}</strong>
              <span className="phone-status">{ended ? "Call ended" : "Live call"}</span>
            </div>
          </div>
          {/* Scrollable, so keyboard users can read back through it too. */}
          {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
          <ol
            className="chat-lines"
            tabIndex={0}
            aria-label="The conversation"
            ref={lines}
            onWheel={stopFollowing}
            onTouchStart={stopFollowing}
          >
            {useCase.lines.slice(0, shown).map(([role, said]) => (
              <li key={said} className={role}>
                {said}
              </li>
            ))}
          </ol>
          <div className="phone-foot">
            <span className="voice-bars" aria-hidden="true">
              <i />
              <i />
              <i />
              <i />
              <i />
            </span>
            <span className="chat-outcome">{ended ? useCase.outcome : ""}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

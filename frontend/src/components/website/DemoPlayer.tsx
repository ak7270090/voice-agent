"use client";

import { useEffect, useRef, useState } from "react";

import { type Demo, DEMOS } from "@/lib/website/content";

type TranscriptLine = { at: number; role: string; text: string };

export function DemoPlayer() {
  const [demo, setDemo] = useState<Demo>(DEMOS[0]);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [now, setNow] = useState(-1);
  const video = useRef<HTMLVideoElement>(null);
  const transcript = useRef<HTMLOListElement>(null);

  useEffect(() => {
    let stale = false;
    setLines([]);
    setNow(-1);
    if (!demo.transcript) return;
    fetch(demo.transcript)
      .then(
        (response) => (response.ok ? response.json() : []),
        () => [],
      )
      .then((loaded) => {
        if (!stale) setLines(loaded);
      });
    return () => {
      stale = true;
    };
  }, [demo]);

  // "Watch" buttons anywhere on the page also start the video, not only scroll to it.
  useEffect(() => {
    const buttons = document.querySelectorAll('a[href="#demo"]');
    const play = () => {
      video.current?.play().catch(() => {});
    };
    buttons.forEach((button) => button.addEventListener("click", play));
    return () => buttons.forEach((button) => button.removeEventListener("click", play));
  }, []);

  useEffect(() => {
    if (now >= 0) {
      transcript.current?.children[now]?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [now]);

  function followVideo() {
    const time = video.current?.currentTime ?? 0;
    setNow(lines.reduce((current, line, index) => (line.at <= time ? index : current), -1));
  }

  function seek(line: TranscriptLine) {
    if (!video.current) return;
    video.current.currentTime = line.at;
    video.current.play().catch(() => {});
  }

  return (
    <div className="player">
      <div className="player-tabs" role="tablist">
        {DEMOS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={item.id === demo.id}
            onClick={() => setDemo(item)}
          >
            {item.tab}
          </button>
        ))}
      </div>
      <div className="player-body">
        <div className="player-stage">
          {/* The poster is in the page's first HTML, and the video only downloads once it's played. */}
          <video
            key={demo.id}
            ref={video}
            className="player-video"
            controls
            playsInline
            preload="none"
            poster={demo.poster}
            src={demo.video}
            onTimeUpdate={followVideo}
          />
        </div>
        <aside className="player-side">
          <h2 className="player-title">{demo.title}</h2>
          <p className="player-text">{demo.text}</p>
          <ol className="player-transcript" ref={transcript}>
            {lines.map((line, index) => (
              <li
                key={`${line.at}-${line.role}`}
                data-role={line.role}
                className={index === now ? "now" : undefined}
                onClick={() => seek(line)}
              >
                <span className="who">{line.role === "agent" ? "Agent" : "Caller"}</span>
                <span className="said">{line.text}</span>
              </li>
            ))}
          </ol>
        </aside>
      </div>
    </div>
  );
}

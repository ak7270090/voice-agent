"use client";

import { type CSSProperties, useCallback, useEffect, useRef, useState } from "react";

import { dashboardPath } from "@/lib/paths";
import {
  type FlowBranch,
  type FlowNode,
  FLOWS,
  NODE_KINDS,
  type NodeKind,
} from "@/lib/website/content";

// The card crossing this line, a little above the middle of the screen, is the one being read.
const READING_LINE = 0.45;
const NAV_CLEARANCE = 88;
const BRANCHES_TITLE = "Where the call can end up";

// {placeholders} look like what they are: values filled in during the call.
function Placeholders({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\{\w+\})/).map((part, index) =>
        /^\{\w+\}$/.test(part) ? (
          <span className="flow-value" key={index}>
            {part.slice(1, -1).replace(/_/g, " ")}
          </span>
        ) : (
          part
        ),
      )}
    </>
  );
}

function FlowCard({
  node,
  kind,
  stop = false,
  active = false,
}: {
  node: FlowNode | FlowBranch;
  kind: NodeKind;
  stop?: boolean;
  active?: boolean;
}) {
  const meta = NODE_KINDS[kind];
  const details = node as FlowNode;
  const loopsBack = (node as FlowBranch).loopsBack;
  return (
    <article
      className={`flow-card ${kind}${active ? " active" : ""}`}
      data-stop={stop ? "" : undefined}
    >
      <span className="flow-kind">{`${meta.icon} ${meta.label}`}</span>
      <h3>{node.name}</h3>
      {details.detail && <p className="flow-detail">{details.detail}</p>}
      {details.says && (
        <p className="flow-says">
          <Placeholders text={details.says} />
        </p>
      )}
      {details.fields && (
        <ul className="flow-fields">
          {details.fields.map((field) => (
            <li key={field}>{field}</li>
          ))}
        </ul>
      )}
      {loopsBack && <p className="flow-loop">{`↩ ${loopsBack}`}</p>}
    </article>
  );
}

function FlowLink({ label }: { label?: string }) {
  return <div className="flow-link">{label && <span>{label}</span>}</div>;
}

export function PlatformFlow() {
  const [flowIndex, setFlowIndex] = useState(0);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const queued = useRef(false);

  const flow = FLOWS[flowIndex];
  const activeNode = flow.nodes[Math.min(active, flow.nodes.length - 1)];

  const highlight = useCallback(() => {
    queued.current = false;
    const line = innerHeight * READING_LINE;
    let nearest = 0;
    let smallest = Infinity;
    root.current?.querySelectorAll("[data-stop]").forEach((stop, index) => {
      const box = stop.getBoundingClientRect();
      const distance = Math.abs((box.top + box.bottom) / 2 - line);
      if (distance < smallest) {
        smallest = distance;
        nearest = index;
      }
    });
    setActive(nearest);
  }, []);

  useEffect(() => {
    function request() {
      if (queued.current) return;
      queued.current = true;
      requestAnimationFrame(highlight);
    }
    addEventListener("scroll", request, { passive: true });
    addEventListener("resize", request);
    return () => {
      removeEventListener("scroll", request);
      removeEventListener("resize", request);
    };
  }, [highlight]);

  // Changing flows changes what is on screen, so the highlight follows.
  useEffect(highlight, [highlight, flowIndex]);

  function chooseFlow(index: number) {
    setFlowIndex(index);
    // Switching flows from further down starts the new one from its top.
    const top = root.current?.getBoundingClientRect().top ?? 0;
    if (top < 0) scrollBy({ top: top - NAV_CLEARANCE, behavior: "instant" });
  }

  return (
    <div className="flow-layout" ref={root}>
      <div className="flow-side">
        <p className="kicker">Platform</p>
        <h2 className="section-title">From an idea to a live phone line</h2>
        <p className="section-lede">
          Draw the conversation, talk to it to test it, then put it on a number. No code.
        </p>
        <div className="flow-tabs" role="tablist" aria-label="Example flows">
          {FLOWS.map((item, index) => (
            <button
              key={item.tab}
              type="button"
              role="tab"
              aria-selected={index === flowIndex}
              onClick={() => chooseFlow(index)}
            >
              {item.tab}
            </button>
          ))}
        </div>
        <div className="flow-note" aria-live="polite">
          <strong>{activeNode.branches ? BRANCHES_TITLE : activeNode.name}</strong>
          <p>{activeNode.why}</p>
        </div>
        <a className="button outline-dark flow-open" href={dashboardPath(flow.demoPath)}>
          {flow.demoPath.endsWith("/flow")
            ? "Open this flow in the demo"
            : "Open the demo workspace"}
        </a>
      </div>
      <div className="flow-canvas">
        {flow.nodes.map((node, position) => {
          const label = position > 0 ? flow.nodes[position - 1].via : undefined;
          return (
            <FlowStop
              key={`${flow.tab}-${position}`}
              node={node}
              showLink={position > 0}
              label={label}
              active={position === active}
            />
          );
        })}
      </div>
    </div>
  );
}

function FlowStop({
  node,
  showLink,
  label,
  active,
}: {
  node: FlowNode;
  showLink: boolean;
  label?: string;
  active: boolean;
}) {
  if (!node.branches) {
    return (
      <>
        {showLink && <FlowLink label={label} />}
        <FlowCard node={node} kind={node.kind ?? "step"} stop active={active} />
      </>
    );
  }
  return (
    <>
      <FlowLink label={label} />
      <div
        className={`flow-branches${active ? " active" : ""}`}
        data-stop=""
        style={{ "--count": node.branches.length } as CSSProperties}
      >
        {node.branches.map((branch) => (
          <div className="flow-arm" key={branch.name}>
            <div className="arm-in">
              <span>{branch.via}</span>
            </div>
            <FlowCard node={branch} kind={branch.kind} />
            {/* An arm that returns to an earlier step doesn't join the line going on. */}
            {!branch.loopsBack && <div className="arm-out" />}
          </div>
        ))}
      </div>
    </>
  );
}

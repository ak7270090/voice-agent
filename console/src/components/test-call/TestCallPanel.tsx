"use client";

import clsx from "clsx";
import { Mic, MicOff, PhoneOff, Play, Send } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { Button, Chip } from "@/components/ui/primitives";

import { useBrowserCall } from "./useBrowserCall";

const AGENT_STATE_LABELS: Record<string, string> = {
  initializing: "Connecting…",
  listening: "Online",
  thinking: "Thinking…",
  speaking: "Speaking",
};

export function TestCallPanel({
  agentId,
  onCallEnded,
  onFlowNode,
}: {
  agentId: string;
  onCallEnded: () => void;
  onFlowNode?: (nodeId: string | null, fields: Record<string, unknown>) => void;
}) {
  const call = useBrowserCall(agentId);

  useEffect(() => {
    onFlowNode?.(call.flowNode, call.flowFields);
  }, [call.flowNode, call.flowFields, onFlowNode]);
  const [draft, setDraft] = useState("");
  const messagesEnd = useRef<HTMLDivElement>(null);
  const previousStatus = useRef(call.status);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ block: "end" });
  }, [call.messages]);

  useEffect(() => {
    if (previousStatus.current === "connected" && call.status === "idle") onCallEnded();
    previousStatus.current = call.status;
  }, [call.status, onCallEnded]);

  function submit(event: FormEvent) {
    event.preventDefault();
    call.send(draft);
    setDraft("");
  }

  const connected = call.status === "connected";
  const stateLabel =
    call.agentState === "listening" && call.voiceOn
      ? "Listening"
      : (AGENT_STATE_LABELS[call.agentState] ?? call.agentState);

  return (
    <div className="flex h-full min-h-[560px] flex-col rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
        <h3 className="text-[13px] font-semibold">Test call</h3>
        {connected ? (
          <Chip tone="green" dot>
            {stateLabel}
          </Chip>
        ) : (
          <Chip>{call.status === "connecting" ? "Connecting…" : "Not started"}</Chip>
        )}
        {connected && (
          <Chip tone={call.voiceOn ? "brand" : "neutral"}>{call.voiceOn ? "Voice" : "Chat"}</Chip>
        )}
        <span className="ml-auto">
          {connected ? (
            <Button variant="danger" onClick={call.end}>
              <PhoneOff size={14} /> End
            </Button>
          ) : (
            <Button variant="primary" onClick={call.start} disabled={call.status === "connecting"}>
              <Play size={14} /> Start test call
            </Button>
          )}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto p-4">
        {call.status === "idle" && call.messages.length === 0 && (
          <p className="m-auto max-w-[260px] text-center text-[13px] text-slate-400">
            Starts as a text chat. Press the mic to talk; the agent then answers in voice.
          </p>
        )}
        {call.messages.map((message) => (
          <div
            key={message.id}
            className={clsx(
              "max-w-[86%] rounded-xl px-3 py-2 text-[13px] leading-relaxed",
              message.speaker === "agent"
                ? "self-start rounded-tl-sm bg-slate-100"
                : "self-end rounded-tr-sm bg-brand-600 text-white",
              message.interim && "opacity-60",
            )}
          >
            {message.text}
          </div>
        ))}
        {call.endNote && <p className="self-center text-xs text-slate-400">{call.endNote}</p>}
        <div ref={messagesEnd} />
      </div>

      {Object.keys(call.flowFields).length > 0 && (
        <div className="border-t border-slate-100 px-4 py-2.5">
          <h4 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Collected fields
          </h4>
          <dl className="grid grid-cols-[100px_1fr] gap-y-1 text-xs">
            {Object.entries(call.flowFields).map(([name, value]) => (
              <div key={name} className="contents">
                <dt className="text-slate-500">{name}</dt>
                <dd className="text-slate-800">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {call.error && (
        <p className="mx-4 mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
          {call.error}
        </p>
      )}

      <form
        onSubmit={submit}
        className="flex items-center gap-2 border-t border-slate-100 px-3 py-2.5"
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={!connected}
          placeholder={call.voiceOn ? "Speak, or type here…" : "Type a message…"}
          className="flex-1 rounded-full border border-slate-200 px-3.5 py-2 text-[13px] outline-none focus:border-brand-500 disabled:bg-slate-50"
        />
        <button
          type="submit"
          disabled={!connected || !draft.trim()}
          aria-label="Send"
          className="grid h-9 w-9 place-items-center rounded-full text-brand-600 hover:bg-brand-50 disabled:text-slate-300"
        >
          <Send size={16} />
        </button>
        <button
          type="button"
          onClick={call.toggleVoice}
          disabled={!connected}
          aria-pressed={call.voiceOn}
          aria-label={call.voiceOn ? "Turn voice off" : "Turn voice on"}
          className={clsx(
            "grid h-9 w-9 place-items-center rounded-full disabled:bg-slate-200",
            call.voiceOn ? "bg-red-500 text-white" : "bg-brand-600 text-white",
          )}
        >
          {call.voiceOn ? <MicOff size={16} /> : <Mic size={16} />}
        </button>
      </form>
    </div>
  );
}

"use client";

import { type FormEvent, type ReactNode, useState } from "react";

import { Button, Card } from "@/components/ui/primitives";
import type { Agent, AgentUpdate } from "@/lib/api";
import { VOICE_OPTIONS } from "@/lib/constants";

const INPUT_CLASS =
  "w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] outline-none focus:border-brand-500";

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      {children}
      {hint && <span className="text-[11px] text-slate-400">{hint}</span>}
    </label>
  );
}

export function AgentEditor({
  agent,
  saving,
  onSave,
}: {
  agent: Agent;
  saving: boolean;
  onSave: (changes: AgentUpdate) => void;
}) {
  const language = agent.languages[0];
  const [name, setName] = useState(agent.name);
  const [greeting, setGreeting] = useState(agent.greeting);
  const [instructions, setInstructions] = useState(agent.instructions);
  const [llmModel, setLlmModel] = useState(agent.llm_model);
  const [voice, setVoice] = useState(agent.language_settings[language].voice);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave({
      name,
      greeting,
      instructions,
      llm_model: llmModel,
      language_settings: {
        ...agent.language_settings,
        [language]: { ...agent.language_settings[language], voice },
      },
    });
  }

  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-4 p-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Name">
            <input className={INPUT_CLASS} value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="LLM" hint="LangChain model string, e.g. openai:gpt-4.1-mini">
            <input
              className={INPUT_CLASS}
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
            />
          </Field>
        </div>
        <Field label="Greeting" hint="The first thing the agent says">
          <input
            className={INPUT_CLASS}
            value={greeting}
            onChange={(e) => setGreeting(e.target.value)}
          />
        </Field>
        <Field label="Instructions" hint="Who the agent is and what it should do">
          <textarea
            className={`${INPUT_CLASS} min-h-[180px] font-mono text-xs leading-relaxed`}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Voice" hint={agent.language_settings[language].tts_model}>
            <select
              className={INPUT_CLASS}
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
            >
              {VOICE_OPTIONS.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </Field>
          <Field label="Speech-to-text">
            <input
              className={`${INPUT_CLASS} bg-slate-50 text-slate-500`}
              value={agent.language_settings[language].stt_model}
              readOnly
            />
          </Field>
        </div>
        <div className="flex justify-end">
          <Button type="submit" variant="primary" disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

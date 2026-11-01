"use client";

import { type FormEvent, type ReactNode, useState } from "react";

import { AnalysisSettings } from "@/components/agents/AnalysisSettings";
import { Button, Card } from "@/components/ui/primitives";
import type { Agent, AgentUpdate, KnowledgeBase } from "@/lib/api";
import { STT_CHOICES, VOICE_CHOICES } from "@/lib/constants";

const voiceKey = (ttsModel: string, voice: string) => `${ttsModel}|${voice}`;

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
  knowledgeBases,
  saving,
  onSave,
}: {
  agent: Agent;
  knowledgeBases: KnowledgeBase[];
  saving: boolean;
  onSave: (changes: AgentUpdate) => void;
}) {
  const language = agent.languages[0];
  const [linkedBases, setLinkedBases] = useState<string[]>(agent.knowledge_base_ids);
  const [name, setName] = useState(agent.name);
  const [greeting, setGreeting] = useState(agent.greeting);
  const [voicemailMessage, setVoicemailMessage] = useState(agent.voicemail_message);
  const [instructions, setInstructions] = useState(agent.instructions);
  const [llmModel, setLlmModel] = useState(agent.llm_model);
  const speech = agent.language_settings[language];
  const [voiceChoice, setVoiceChoice] = useState(voiceKey(speech.tts_model, speech.voice));
  const [sttModel, setSttModel] = useState(speech.stt_model);
  const [analysisFields, setAnalysisFields] = useState(agent.analysis_fields);
  const [successRule, setSuccessRule] = useState(agent.success_rule);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave({
      name,
      greeting,
      voicemail_message: voicemailMessage,
      instructions,
      llm_model: llmModel,
      knowledge_base_ids: linkedBases,
      analysis_fields: analysisFields,
      success_rule: successRule,
      language_settings: {
        ...agent.language_settings,
        [language]: {
          stt_model: sttModel,
          tts_model: voiceChoice.split("|")[0],
          voice: voiceChoice.split("|")[1],
        },
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
          <Field label="LLM" hint="LangChain model string, e.g. openai:gpt-5.4-mini">
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
        <Field
          label="Voicemail message"
          hint="Left when an outgoing call reaches voicemail; empty hangs up instead"
        >
          <input
            className={INPUT_CLASS}
            value={voicemailMessage}
            placeholder="e.g. Hi, this is City Clinic. Please call us back at your convenience."
            onChange={(e) => setVoicemailMessage(e.target.value)}
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
          <Field label="Voice" hint="Deepgram starts speaking sooner; OpenAI has more voices">
            <select
              className={INPUT_CLASS}
              value={voiceChoice}
              onChange={(e) => setVoiceChoice(e.target.value)}
            >
              {VOICE_CHOICES.map((choice) => (
                <option key={choice.label} value={voiceKey(choice.tts_model, choice.voice)}>
                  {choice.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Speech-to-text">
            <select
              className={INPUT_CLASS}
              value={sttModel}
              onChange={(e) => setSttModel(e.target.value)}
            >
              {STT_CHOICES.map((choice) => (
                <option key={choice.stt_model} value={choice.stt_model}>
                  {choice.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field
          label="Knowledge bases"
          hint="The agent searches these before answering questions about the business"
        >
          <div className="flex flex-wrap gap-2">
            {knowledgeBases.length === 0 && (
              <span className="text-[13px] text-slate-400">
                None yet. Create one on the Knowledge page.
              </span>
            )}
            {knowledgeBases.map((knowledgeBase) => (
              <label
                key={knowledgeBase.id}
                className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-[13px]"
              >
                <input
                  type="checkbox"
                  checked={linkedBases.includes(knowledgeBase.id)}
                  onChange={(event) =>
                    setLinkedBases((current) =>
                      event.target.checked
                        ? [...current, knowledgeBase.id]
                        : current.filter((id) => id !== knowledgeBase.id),
                    )
                  }
                />
                {knowledgeBase.name}
                <span className="text-xs text-slate-400">{knowledgeBase.chunk_count} chunks</span>
              </label>
            ))}
          </div>
        </Field>
        <AnalysisSettings
          fields={analysisFields}
          successRule={successRule}
          onFieldsChange={setAnalysisFields}
          onSuccessRuleChange={setSuccessRule}
        />
        <div className="flex justify-end">
          <Button type="submit" variant="primary" disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

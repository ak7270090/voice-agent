export const LANGUAGE_LABELS: Record<string, string> = { en: "English", hi: "Hindi" };

// A voice is a text-to-speech model plus, for OpenAI, a voice name (Deepgram puts the voice in
// the model name).
export const VOICE_CHOICES = [
  ...["thalia", "andromeda", "helena", "apollo", "arcas", "asteria"].map((name) => ({
    label: `Deepgram Aura-2 · ${name} (fastest)`,
    tts_model: `deepgram/aura-2-${name}-en`,
    voice: "",
  })),
  ...["alloy", "ash", "coral", "echo", "nova", "sage", "shimmer"].map((name) => ({
    label: `OpenAI tts-1 · ${name}`,
    tts_model: "openai/tts-1",
    voice: name,
  })),
];

export const voiceLabel = (ttsModel: string, voice: string) =>
  VOICE_CHOICES.find(
    (choice) => choice.tts_model === ttsModel && choice.voice === voice,
  )?.label.replace(/ \(.*\)$/, "") ??
  (voice || ttsModel);

// LangChain model strings; any other one can still be typed in ("Other model").
export const LLM_CHOICES = [
  { label: "OpenAI GPT-5.4 mini (recommended)", llm_model: "openai:gpt-5.4-mini" },
  { label: "OpenAI GPT-4.1", llm_model: "openai:gpt-4.1" },
  { label: "OpenAI GPT-4.1 mini", llm_model: "openai:gpt-4.1-mini" },
  { label: "OpenAI GPT-4.1 nano (fastest)", llm_model: "openai:gpt-4.1-nano" },
];

export const llmLabel = (model: string) =>
  LLM_CHOICES.find((choice) => choice.llm_model === model)?.label.replace(/ \(.*\)$/, "") ?? model;

export const TIME_ZONE_CHOICES = [
  { label: "India (Asia/Kolkata)", value: "Asia/Kolkata" },
  { label: "UAE (Asia/Dubai)", value: "Asia/Dubai" },
  { label: "Singapore (Asia/Singapore)", value: "Asia/Singapore" },
  { label: "UK (Europe/London)", value: "Europe/London" },
  { label: "Central Europe (Europe/Berlin)", value: "Europe/Berlin" },
  { label: "US Eastern (America/New_York)", value: "America/New_York" },
  { label: "US Central (America/Chicago)", value: "America/Chicago" },
  { label: "US Pacific (America/Los_Angeles)", value: "America/Los_Angeles" },
  { label: "Australia Eastern (Australia/Sydney)", value: "Australia/Sydney" },
  { label: "UTC", value: "UTC" },
];

export const STT_CHOICES = [
  { label: "Deepgram nova-3 (fastest)", stt_model: "deepgram/nova-3" },
  { label: "OpenAI gpt-4o-mini-transcribe", stt_model: "openai/gpt-4o-mini-transcribe" },
];

export const TEMPLATE_STYLES: Record<string, { icon: string; tint: string }> = {
  "clinic-booking": { icon: "✚", tint: "bg-brand-50 text-brand-600" },
  "clinic-booking-calcom": { icon: "◷", tint: "bg-emerald-50 text-emerald-600" },
  "appointment-reminder": { icon: "⏰", tint: "bg-sky-50 text-sky-600" },
  "lead-qualifier": { icon: "★", tint: "bg-violet-50 text-violet-600" },
  "delivery-follow-up": { icon: "⛟", tint: "bg-amber-50 text-amber-700" },
};

export const DEFAULT_TEMPLATE_STYLE = { icon: "◆", tint: "bg-slate-100 text-slate-600" };

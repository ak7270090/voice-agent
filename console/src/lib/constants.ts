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

export const STT_CHOICES = [
  { label: "Deepgram nova-3 (fastest)", stt_model: "deepgram/nova-3" },
  { label: "OpenAI gpt-4o-mini-transcribe", stt_model: "openai/gpt-4o-mini-transcribe" },
];

export const TEMPLATE_STYLES: Record<string, { icon: string; tint: string }> = {
  "clinic-booking": { icon: "✚", tint: "bg-brand-50 text-brand-600" },
  "appointment-reminder": { icon: "⏰", tint: "bg-sky-50 text-sky-600" },
  "lead-qualifier": { icon: "★", tint: "bg-violet-50 text-violet-600" },
  "delivery-follow-up": { icon: "⛟", tint: "bg-amber-50 text-amber-700" },
};

export const DEFAULT_TEMPLATE_STYLE = { icon: "◆", tint: "bg-slate-100 text-slate-600" };

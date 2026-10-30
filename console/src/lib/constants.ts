export const LANGUAGE_LABELS: Record<string, string> = { en: "English", hi: "Hindi" };

// OpenAI text-to-speech voices; other providers come with Phase 8.
export const VOICE_OPTIONS = [
  "alloy",
  "ash",
  "coral",
  "echo",
  "fable",
  "nova",
  "onyx",
  "sage",
  "shimmer",
];

export const TEMPLATE_STYLES: Record<string, { icon: string; tint: string }> = {
  "clinic-booking": { icon: "✚", tint: "bg-brand-50 text-brand-600" },
  "appointment-reminder": { icon: "⏰", tint: "bg-sky-50 text-sky-600" },
  "lead-qualifier": { icon: "★", tint: "bg-violet-50 text-violet-600" },
  "delivery-follow-up": { icon: "⛟", tint: "bg-amber-50 text-amber-700" },
};

export const DEFAULT_TEMPLATE_STYLE = { icon: "◆", tint: "bg-slate-100 text-slate-600" };

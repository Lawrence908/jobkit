/**
 * LLM model options for chat completions (e.g. OpenRouter).
 * Empty value = use server default (LLM_MODEL).
 * Update this list when you add or change models.
 */
export const LLM_MODEL_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Default - Claude 4.6 Sonnet" },
  { value: "openai/gpt-4.1-mini", label: "GPT-4.1 mini" },
  { value: "openai/gpt-5.4", label: "GPT-5.4" },
  { value: "anthropic/claude-sonnet-4.6", label: "Claude 4.6 Sonnet" },
  { value: "anthropic/claude-haiku-4.5", label: "Claude 4.5 Haiku" },
  { value: "google/gemini-3-flash-preview", label: "Gemini 3 Flash Preview" },
];

/**
 * LLM provider and model options for profile. Used for generation (resume/cover/notes).
 * Backend maps provider to base URL: openrouter -> openrouter.ai, openai -> api.openai.com, anthropic -> api.anthropic.com.
 */
export const LLM_PROVIDER_OPTIONS = [
  { value: "openrouter", label: "OpenRouter (default)" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
] as const;

export type LLMProvider = (typeof LLM_PROVIDER_OPTIONS)[number]["value"];

/** Model options per provider. Value is sent to API as-is (OpenRouter uses e.g. anthropic/claude-*). */
export const LLM_MODEL_OPTIONS_BY_PROVIDER: Record<LLMProvider, { value: string; label: string }[]> = {
  openrouter: [
    { value: "anthropic/claude-sonnet-4.6", label: "Claude 4.6 Sonnet" },
    { value: "anthropic/claude-haiku-4.5", label: "Claude 4.5 Haiku" },
    { value: "openai/gpt-4.1-mini", label: "GPT-4.1 mini" },
    { value: "openai/gpt-5.4", label: "GPT-5.4" },
    { value: "google/gemini-3-flash-preview", label: "Gemini 3 Flash Preview" },
  ],
  openai: [
    { value: "gpt-4.1-mini", label: "GPT-4.1 mini" },
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4o-mini", label: "GPT-4o mini" },
    { value: "gpt-5.4", label: "GPT-5.4" },
  ],
  anthropic: [
    { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
    { value: "claude-3-5-sonnet-20241022", label: "Claude 3.5 Sonnet" },
    { value: "claude-3-5-haiku-20241022", label: "Claude 3.5 Haiku" },
  ],
};

export const DEFAULT_MODEL_BY_PROVIDER: Record<LLMProvider, string> = {
  openrouter: "anthropic/claude-sonnet-4.6",
  openai: "gpt-4.1-mini",
  anthropic: "claude-sonnet-4-20250514",
};

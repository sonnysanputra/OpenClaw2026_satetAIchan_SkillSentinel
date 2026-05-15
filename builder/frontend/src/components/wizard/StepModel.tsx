"use client";
import { useWizard } from "@/store/wizard";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const PROVIDERS = [
  "anthropic",
  "openai",
  "gemini",
  "openrouter",
  "ollama",
] as const;

const MODELS: Record<
  (typeof PROVIDERS)[number],
  { id: string; tag?: string }[]
> = {
  anthropic: [
    { id: "claude-opus-4-6", tag: "capable" },
    { id: "claude-sonnet-4-6", tag: "balanced" },
    { id: "claude-haiku-4-5-20251001", tag: "fast" },
    { id: "claude-sonnet-4-20250514" },
  ],
  openai: [
    { id: "gpt-4o", tag: "capable" },
    { id: "gpt-4o-mini", tag: "fast" },
    { id: "o3-mini", tag: "reasoning" },
  ],
  gemini: [
    { id: "gemini-2.5-pro", tag: "capable" },
    { id: "gemini-2.5-flash", tag: "balanced" },
    { id: "gemini-2.0-flash", tag: "fast" },
  ],
  openrouter: [
    { id: "openrouter/moonshotai/kimi-k2" },
    { id: "openrouter/meta-llama/llama-3.1-70b" },
  ],
  ollama: [
    { id: "ollama/llama3.3" },
    { id: "ollama/mistral" },
    { id: "ollama/gemma3:27b" },
  ],
};

export function StepModel() {
  const m = useWizard((s) => s.model);
  const update = useWizard((s) => s.updateModel);

  function onProvider(p: (typeof PROVIDERS)[number]) {
    update({ provider: p, model: MODELS[p][0].id });
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Model</h2>
        <p className="text-sm text-muted-foreground">
          Pick a provider and primary model.
        </p>
      </div>
      <div>
        <Label>Provider</Label>
        <div className="mt-2 flex flex-wrap gap-2">
          {PROVIDERS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => onProvider(p)}
              className={cn(
                "rounded-md border px-3 py-1.5 text-sm transition",
                m.provider === p
                  ? "border-primary bg-accent"
                  : "border-input hover:bg-accent",
              )}
            >
              {p}
            </button>
          ))}
        </div>
      </div>
      <div>
        <Label>Model</Label>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {MODELS[m.provider as keyof typeof MODELS]?.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => update({ model: opt.id })}
              className={cn(
                "flex items-center justify-between rounded-md border px-3 py-2 text-left text-sm transition",
                m.model === opt.id
                  ? "border-primary bg-accent"
                  : "border-input hover:bg-accent",
              )}
            >
              <span className="font-mono text-xs">{opt.id}</span>
              {opt.tag && (
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                  {opt.tag}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
      <div>
        <Label>Heartbeat model (optional, cheaper)</Label>
        <Input
          value={m.heartbeat_model}
          onChange={(e) => update({ heartbeat_model: e.target.value })}
          placeholder={`${m.provider}/${MODELS[m.provider as keyof typeof MODELS]?.[0]?.id}`}
        />
      </div>
      {m.provider !== "ollama" && (
        <div>
          <Label>API Key (required for {m.provider})</Label>
          <Input
            type="password"
            value={m.api_key}
            onChange={(e) => update({ api_key: e.target.value })}
            placeholder={`sk-...`}
          />
        </div>
      )}
    </div>
  );
}

export function validateModel(s: ReturnType<typeof useWizard.getState>) {
  if (!s.model.provider || !s.model.model) return false;
  if (s.model.provider !== "ollama" && !s.model.api_key) return false;
  return true;
}

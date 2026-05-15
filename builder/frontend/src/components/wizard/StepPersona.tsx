"use client";
import { useWizard } from "@/store/wizard";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const TONES = ["casual", "friendly", "professional", "formal", "direct", "playful"];
const TRAITS = ["curious", "concise", "empathetic", "proactive", "direct", "witty", "patient", "thorough", "creative", "analytical"];

function Chip({ active, children, onClick }: { active: boolean; children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-sm transition",
        active ? "border-primary bg-primary text-primary-foreground" : "border-input hover:bg-accent"
      )}
    >
      {children}
    </button>
  );
}

export function StepPersona() {
  const p = useWizard((s) => s.persona);
  const update = useWizard((s) => s.updatePersona);

  function toggleTrait(t: string) {
    update({
      traits: p.traits.includes(t) ? p.traits.filter((x) => x !== t) : [...p.traits, t],
    });
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Persona</h2>
        <p className="text-sm text-muted-foreground">Generates <code>SOUL.md</code>.</p>
      </div>
      <div>
        <Label>Tone</Label>
        <div className="mt-2 flex flex-wrap gap-2">
          {TONES.map((t) => (
            <Chip key={t} active={p.tone === t} onClick={() => update({ tone: t })}>{t}</Chip>
          ))}
        </div>
      </div>
      <div>
        <Label>Traits (pick any)</Label>
        <div className="mt-2 flex flex-wrap gap-2">
          {TRAITS.map((t) => (
            <Chip key={t} active={p.traits.includes(t)} onClick={() => toggleTrait(t)}>{t}</Chip>
          ))}
        </div>
      </div>
      <div>
        <Label htmlFor="avoid">Things this agent should never do (optional)</Label>
        <Textarea id="avoid" rows={3} value={p.avoid} onChange={(e) => update({ avoid: e.target.value })} />
      </div>
    </div>
  );
}

export function validatePersona(s: ReturnType<typeof useWizard.getState>) {
  return Boolean(s.persona.tone);
}

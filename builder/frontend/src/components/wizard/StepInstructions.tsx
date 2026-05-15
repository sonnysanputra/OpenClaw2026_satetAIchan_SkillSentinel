"use client";
import { useWizard } from "@/store/wizard";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

const GROUP_CHAT = [
  { value: "mention", label: "Require @mention", desc: "Only respond when explicitly tagged." },
  { value: "all", label: "Respond to all", desc: "Chime in on every message." },
  { value: "silent", label: "Stay silent", desc: "Don't speak unless DM'd." },
] as const;

export function StepInstructions() {
  const inst = useWizard((s) => s.instructions);
  const update = useWizard((s) => s.updateInstructions);
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Instructions</h2>
        <p className="text-sm text-muted-foreground">Generates <code>AGENTS.md</code>.</p>
      </div>
      <div>
        <Label>Primary responsibilities</Label>
        <Textarea
          rows={4}
          value={inst.responsibilities}
          onChange={(e) => update({ responsibilities: e.target.value })}
          placeholder="Triage support inbox, escalate billing questions, draft replies in my voice…"
        />
      </div>
      <div>
        <Label>Memory rules (optional)</Label>
        <Textarea
          rows={3}
          value={inst.memory_rules}
          onChange={(e) => update({ memory_rules: e.target.value })}
        />
      </div>
      <div>
        <Label>Group chats</Label>
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          {GROUP_CHAT.map((g) => (
            <button
              key={g.value}
              type="button"
              onClick={() => update({ group_chat: g.value })}
              className={cn(
                "rounded-md border p-3 text-left transition",
                inst.group_chat === g.value ? "border-primary bg-accent" : "border-input hover:bg-accent"
              )}
            >
              <div className="text-sm font-medium">{g.label}</div>
              <div className="text-xs text-muted-foreground">{g.desc}</div>
            </button>
          ))}
        </div>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <Checkbox
          checked={inst.security_rules}
          onCheckedChange={(c) => update({ security_rules: Boolean(c) })}
        />
        Inject SkillsSentinel-style security block into AGENTS.md (recommended)
      </label>
    </div>
  );
}

export function validateInstructions(s: ReturnType<typeof useWizard.getState>) {
  return Boolean(s.instructions.responsibilities.trim());
}

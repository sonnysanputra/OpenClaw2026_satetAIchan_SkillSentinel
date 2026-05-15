"use client";
import { useWizard } from "@/store/wizard";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const CHANNELS = [
  { id: "telegram", name: "Telegram", icon: "✈️", difficulty: "Easy" },
  { id: "whatsapp", name: "WhatsApp", icon: "🟢", difficulty: "Medium" },
  { id: "discord", name: "Discord", icon: "🎮", difficulty: "Easy" },
  { id: "slack", name: "Slack", icon: "💬", difficulty: "Medium" },
  { id: "signal", name: "Signal", icon: "🔵", difficulty: "Advanced" },
  { id: "imessage", name: "iMessage", icon: "💙", difficulty: "Mac only" },
  { id: "line", name: "LINE", icon: "🟩", difficulty: "Medium" },
  { id: "matrix", name: "Matrix", icon: "🟦", difficulty: "Advanced" },
];

export function StepChannels() {
  const ch = useWizard((s) => s.channels);
  const update = useWizard((s) => s.updateChannels);

  function toggle(id: string) {
    const selected = ch.selected.includes(id) ? ch.selected.filter((x) => x !== id) : [...ch.selected, id];
    update({ selected });
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Channels</h2>
        <p className="text-sm text-muted-foreground">Where should the agent listen and reply? OAuth flows are completed manually after deploy.</p>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {CHANNELS.map((c) => {
          const on = ch.selected.includes(c.id);
          return (
            <button
              type="button"
              key={c.id}
              onClick={() => toggle(c.id)}
              className={cn(
                "rounded-md border p-3 text-left transition",
                on ? "border-primary bg-accent" : "border-input hover:bg-accent"
              )}
            >
              <div className="text-lg">{c.icon}</div>
              <div className="text-sm font-medium">{c.name}</div>
              <div className="text-xs text-muted-foreground">{c.difficulty}</div>
            </button>
          );
        })}
      </div>
      {ch.selected.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-medium">Account IDs (optional)</div>
          {ch.selected.map((id) => (
            <div key={id} className="flex items-center gap-3">
              <span className="w-20 text-sm capitalize text-muted-foreground">{id}</span>
              <Input
                placeholder="leave blank for default"
                value={ch.account_ids[id] || ""}
                onChange={(e) => update({ account_ids: { ...ch.account_ids, [id]: e.target.value } })}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function validateChannels() { return true; }

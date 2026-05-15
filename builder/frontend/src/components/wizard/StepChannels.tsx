"use client";
import { useWizard } from "@/store/wizard";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface ProviderField {
  key: string;
  label: string;
  placeholder: string;
  secret?: boolean;
}

const CHANNEL_FIELDS: Record<string, ProviderField[]> = {
  telegram: [
    { key: "bot_token", label: "Bot Token", placeholder: "1234567890:ABCdefGHI...", secret: true },
  ],
  discord: [
    { key: "bot_token", label: "Bot Token", placeholder: "MTxxxxxxx.Gyyyyy.Zzzzz...", secret: true },
    { key: "guild_id", label: "Server ID", placeholder: "123456789012345678" },
    { key: "channel_id", label: "Channel ID", placeholder: "123456789012345678" },
  ],
  slack: [
    { key: "bot_token", label: "Bot Token (xoxb-...)", placeholder: "xoxb-000000000000-...", secret: true },
    { key: "app_token", label: "App Token (xapp-...)", placeholder: "xapp-1-...", secret: true },
    { key: "channel_id", label: "Channel ID (optional)", placeholder: "C0XXXXXXX" },
  ],
  whatsapp: [
    { key: "phone_number_id", label: "Phone Number ID", placeholder: "123456789012345" },
    { key: "access_token", label: "Access Token", placeholder: "EAAxxxx...", secret: true },
    { key: "webhook_verify_token", label: "Webhook Verify Token", placeholder: "my-verify-token", secret: true },
  ],
  signal: [
    { key: "phone_number", label: "Linked Phone Number", placeholder: "+1234567890" },
  ],
  imessage: [
    { key: "apple_id", label: "Apple ID", placeholder: "user@example.com" },
  ],
  line: [
    { key: "channel_access_token", label: "Channel Access Token", placeholder: "xxxxxxxx...", secret: true },
    { key: "channel_secret", label: "Channel Secret", placeholder: "abcdef1234567890", secret: true },
  ],
  matrix: [
    { key: "homeserver_url", label: "Homeserver URL", placeholder: "https://matrix.org" },
    { key: "access_token", label: "Access Token", placeholder: "syt_xxx...", secret: true },
    { key: "room_id", label: "Room ID", placeholder: "!roomid:matrix.org" },
  ],
};

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
    const selected = ch.selected.includes(id)
      ? ch.selected.filter((x) => x !== id)
      : [...ch.selected, id];
    update({ selected });
  }

  function setField(provider: string, fieldKey: string, value: string) {
    const existing = ch.channel_fields[provider] ?? {};
    update({
      channel_fields: {
        ...ch.channel_fields,
        [provider]: { ...existing, [fieldKey]: value },
      },
    });
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Channels</h2>
        <p className="text-sm text-muted-foreground">
          Where should the agent listen and reply? Credentials are written to the VPS during deploy.
        </p>
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
        <div className="space-y-5">
          {ch.selected.map((id) => {
            const fields = CHANNEL_FIELDS[id] ?? [];
            const channelMeta = CHANNELS.find((c) => c.id === id);
            const values = ch.channel_fields[id] ?? {};
            return (
              <div key={id} className="rounded-md border p-4 space-y-3">
                <div className="text-sm font-semibold">
                  {channelMeta?.icon} {channelMeta?.name ?? id}
                </div>
                {fields.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No configuration required.</p>
                ) : (
                  fields.map((f) => (
                    <div key={f.key} className="space-y-1">
                      <label className="text-xs font-medium text-muted-foreground">
                        {f.label}
                      </label>
                      <Input
                        type={f.secret ? "password" : "text"}
                        placeholder={f.placeholder}
                        value={values[f.key] ?? ""}
                        onChange={(e) => setField(id, f.key, e.target.value)}
                        autoComplete="off"
                      />
                    </div>
                  ))
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function validateChannels() { return true; }

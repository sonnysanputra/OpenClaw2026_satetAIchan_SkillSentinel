"use client";
import { useEffect } from "react";
import { useWizard } from "@/store/wizard";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { slugify } from "@/lib/utils";

const EMOJIS = ["🦞", "🐙", "🦊", "🦉", "🦋", "🐢", "🐈", "🪼", "🦦", "🦤", "🦜", "🦩", "🐉", "🦝", "🐧", "🐳"];

export function StepIdentity() {
  const id = useWizard((s) => s.identity);
  const update = useWizard((s) => s.updateIdentity);
  const manualEdit = useWizard((s) => s.workspaceManuallyEdited);
  const setManualEdit = useWizard((s) => s.setWorkspaceManuallyEdited);

  // Auto-derive agent_id when agent_name changes
  useEffect(() => {
    const derived = slugify(id.agent_name);
    if (derived && derived !== id.agent_id) {
      update({ agent_id: derived });
    }
  }, [id.agent_name]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-derive workspace_path when agent_id changes (unless user typed their own)
  useEffect(() => {
    if (!manualEdit && id.agent_id) {
      update({ workspace_path: `~/.openclaw/workspace-${id.agent_id}` });
    }
  }, [id.agent_id, manualEdit]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Agent identity</h2>
        <p className="text-sm text-muted-foreground">Name, emoji, and the workspace path on disk.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="agent_name">Display name</Label>
          <Input id="agent_name" placeholder="Aria" value={id.agent_name} onChange={(e) => update({ agent_name: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="agent_id">Slug</Label>
          <Input
            id="agent_id"
            placeholder="aria"
            value={id.agent_id}
            onChange={(e) => update({ agent_id: slugify(e.target.value) })}
          />
        </div>
      </div>
      <div>
        <Label>Emoji</Label>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {EMOJIS.map((e) => (
            <button
              type="button"
              key={e}
              onClick={() => update({ emoji: e })}
              className={`h-9 w-9 rounded-md border text-lg transition hover:bg-accent ${
                id.emoji === e ? "border-primary bg-accent" : "border-input"
              }`}
            >
              {e}
            </button>
          ))}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="theme">Theme (optional)</Label>
          <Input id="theme" placeholder="calm colleague" value={id.theme} onChange={(e) => update({ theme: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="ws">Workspace path</Label>
          <Input
            id="ws"
            value={id.workspace_path}
            onChange={(e) => {
              setManualEdit(true);
              update({ workspace_path: e.target.value });
            }}
          />
        </div>
      </div>
    </div>
  );
}

export function validateIdentity(s: ReturnType<typeof useWizard.getState>): boolean {
  const i = s.identity;
  return Boolean(i.agent_name && i.agent_id && i.emoji && i.workspace_path);
}

"use client";
import { useWizard } from "@/store/wizard";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function StepUserContext() {
  const ctx = useWizard((s) => s.user_context);
  const update = useWizard((s) => s.updateUserContext);
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">About you</h2>
        <p className="text-sm text-muted-foreground">All fields optional. Generates <code>USER.md</code>.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label>Name</Label>
          <Input value={ctx.user_name} onChange={(e) => update({ user_name: e.target.value })} />
        </div>
        <div>
          <Label>Role</Label>
          <Input value={ctx.user_role} onChange={(e) => update({ user_role: e.target.value })} />
        </div>
      </div>
      <div>
        <Label>Location / timezone</Label>
        <Input value={ctx.user_location} onChange={(e) => update({ user_location: e.target.value })} />
      </div>
      <div>
        <Label>Communication preferences</Label>
        <Textarea rows={3} value={ctx.user_prefs} onChange={(e) => update({ user_prefs: e.target.value })} />
      </div>
      <div>
        <Label>Anything else</Label>
        <Textarea rows={3} value={ctx.user_extra} onChange={(e) => update({ user_extra: e.target.value })} />
      </div>
    </div>
  );
}

export function validateUserContext() { return true; }

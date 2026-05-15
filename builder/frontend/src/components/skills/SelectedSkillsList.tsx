"use client";
import { useState } from "react";
import { useWizard } from "@/store/wizard";
import { Button } from "@/components/ui/button";
import { reviewSkills } from "@/lib/api";
import { SecurityBadge } from "./SecurityBadge";
import { Trash2, ShieldCheck, AlertTriangle } from "lucide-react";

export function SelectedSkillsList() {
  const skills = useWizard((s) => s.skills);
  const removeSkill = useWizard((s) => s.removeSkill);
  const patchSkill = useWizard((s) => s.patchSkill);
  const [reviewing, setReviewing] = useState(false);

  async function onReviewAll() {
    const pending = skills.filter((s) => s.security_status === "pending");
    if (pending.length === 0) return;
    setReviewing(true);
    pending.forEach((s) => patchSkill(s.id, { security_status: "reviewing" }));
    try {
      const r = await reviewSkills({
        skills: pending.map((s) => ({ id: s.id, name: s.name, raw_url: s.raw_url, content: s.content })),
      });
      r.results.forEach((res) => {
        patchSkill(res.id, {
          security_status: res.status,
          security_reason: res.reason,
        });
      });
    } catch (e: any) {
      pending.forEach((s) =>
        patchSkill(s.id, {
          security_status: "blocked",
          security_reason: e?.message || "Review failed",
        })
      );
    } finally {
      setReviewing(false);
    }
  }

  return (
    <div className="rounded-lg border p-3">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-medium">Queued skills ({skills.length})</div>
        <Button
          size="sm"
          onClick={onReviewAll}
          disabled={reviewing || !skills.some((s) => s.security_status === "pending")}
        >
          <ShieldCheck className="h-3.5 w-3.5" />
          {reviewing ? "Reviewing…" : "Review all"}
        </Button>
      </div>
      <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
        {skills.length === 0 && (
          <div className="py-8 text-center text-sm text-muted-foreground">No skills queued yet.</div>
        )}
        {skills.map((s) => (
          <div key={s.id} className="rounded-md border p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{s.name}</div>
                <div className="truncate text-xs text-muted-foreground">{s.author}</div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <SecurityBadge status={s.security_status} />
                <Button size="icon" variant="ghost" onClick={() => removeSkill(s.id)} aria-label="Remove">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
            {s.security_status === "blocked" && s.security_reason && (
              <div className="mt-2 rounded bg-destructive/5 p-2 text-xs text-destructive">
                <AlertTriangle className="mr-1 inline h-3 w-3" />
                {s.security_reason}
                <div className="mt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => patchSkill(s.id, { security_status: "overridden" })}
                  >
                    Override (I accept the risk)
                  </Button>
                </div>
              </div>
            )}
            {s.security_status === "overridden" && (
              <div className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                Will install despite block reason: {s.security_reason || "(none recorded)"}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

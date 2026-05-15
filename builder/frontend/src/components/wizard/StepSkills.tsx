"use client";
import { SkillBrowser } from "@/components/skills/SkillBrowser";
import { SelectedSkillsList } from "@/components/skills/SelectedSkillsList";

export function StepSkills() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Skills</h2>
        <p className="text-sm text-muted-foreground">
          Browse SkillsHub, queue what you want. Every selected skill must pass SkillsSentinel before deployment.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <SkillBrowser />
        <SelectedSkillsList />
      </div>
    </div>
  );
}

export function validateSkills() { return true; }

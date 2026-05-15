"use client";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
  "VPS",
  "Identity",
  "Persona",
  "About You",
  "Instructions",
  "Model",
  "Channels",
  "Skills",
  "Review",
];

interface Props {
  current: number;
  maxReached: number;
  onJump: (i: number) => void;
}

export function StepIndicator({ current, maxReached, onJump }: Props) {
  return (
    <ol className="flex w-full flex-wrap items-center gap-2 text-xs text-muted-foreground">
      {STEPS.map((label, i) => {
        const isActive = i === current;
        const isDone = i < current;
        const reachable = i <= maxReached;
        return (
          <li key={label} className="flex items-center gap-2">
            <button
              type="button"
              disabled={!reachable}
              onClick={() => reachable && onJump(i)}
              className={cn(
                "flex h-7 items-center gap-2 rounded-full px-3 transition",
                isActive && "bg-primary text-primary-foreground",
                isDone && !isActive && "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
                !isActive && !isDone && reachable && "border border-input hover:bg-accent",
                !reachable && "cursor-not-allowed opacity-50"
              )}
            >
              {isDone ? <Check className="h-3 w-3" /> : <span className="font-mono">{i + 1}</span>}
              <span className="hidden sm:inline">{label}</span>
            </button>
            {i < STEPS.length - 1 && <span className="text-muted-foreground/50">›</span>}
          </li>
        );
      })}
    </ol>
  );
}

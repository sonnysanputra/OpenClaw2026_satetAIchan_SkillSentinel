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
    <ol className="flex w-full flex-wrap items-center gap-2">
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
                "flex h-7 items-center gap-2 rounded-full px-3 text-xs font-medium transition-all duration-150",
                isActive && "bg-primary text-white shadow-sm",
                isDone && !isActive && "bg-orange-50 text-orange-600 border border-orange-200",
                !isActive && !isDone && reachable && "border border-border text-muted-foreground hover:border-orange-300 hover:text-foreground bg-white",
                !reachable && "cursor-not-allowed opacity-40 text-muted-foreground"
              )}
            >
              <span
                className={cn(
                  "flex h-4 w-4 items-center justify-center rounded-full font-mono text-[10px]",
                  isActive && "bg-white/25",
                  isDone && "bg-orange-100",
                  !isActive && !isDone && "bg-muted"
                )}
              >
                {isDone ? <Check className="h-2.5 w-2.5" /> : i + 1}
              </span>
              <span className="hidden sm:inline">{label}</span>
            </button>
            {i < STEPS.length - 1 && (
              <span className="text-border text-xs">›</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

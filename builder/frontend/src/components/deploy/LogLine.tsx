"use client";
import type { LogMessage } from "@/types";

const ICONS: Record<LogMessage["level"], string> = {
  info: "→",
  success: "✓",
  warning: "⚠",
  error: "✗",
};

const COLORS: Record<LogMessage["level"], string> = {
  info: "text-zinc-400",
  success: "text-emerald-400",
  warning: "text-amber-400",
  error: "text-red-400",
};

export function LogLine({ log }: { log: LogMessage }) {
  return (
    <div className={`flex gap-2 ${COLORS[log.level]}`}>
      <span className="w-4 shrink-0 text-center">{ICONS[log.level]}</span>
      <span className="whitespace-pre-wrap break-words">{log.message}</span>
    </div>
  );
}

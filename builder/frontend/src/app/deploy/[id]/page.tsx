"use client";
import { use, useEffect, useRef } from "react";
import { useDeploySocket } from "@/hooks/useDeploySocket";
import { LogLine } from "@/components/deploy/LogLine";
import { DeployStatusCard } from "@/components/deploy/DeployStatusCard";
import { useWizard } from "@/store/wizard";
import { Loader2 } from "lucide-react";

export default function DeployPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { logs, status } = useDeploySocket(id);
  const scrollRef = useRef<HTMLDivElement>(null);
  const identity = useWizard((s) => s.identity);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [logs.length]);

  const lastError = [...logs].reverse().find((l) => l.level === "error")?.message;

  const statusLabel =
    status === "deploying"
      ? "Deploying…"
      : status === "completed"
      ? "Done"
      : status === "failed"
      ? "Failed"
      : "Connecting…";

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <p className="label-tag">Deployment · {id.slice(0, 8)}</p>
        <h1 className="flex items-center gap-3 text-2xl font-extrabold tracking-tight">
          {status === "deploying" && (
            <Loader2 className="h-5 w-5 animate-spin oc-orange" />
          )}
          {statusLabel}
          {status === "completed" && <span className="oc-orange text-lg">✓</span>}
          {status === "failed" && <span className="text-destructive text-lg">✗</span>}
        </h1>
      </div>

      <div
        ref={scrollRef}
        className="h-[60vh] overflow-auto rounded-xl border border-border bg-zinc-950 p-4 font-mono text-xs text-zinc-200 shadow-inner"
      >
        {logs.length === 0 && (
          <div className="text-zinc-500">Waiting for output…</div>
        )}
        {logs.map((l, i) => (
          <LogLine key={i} log={l} />
        ))}
      </div>

      {(status === "completed" || status === "failed") && (
        <DeployStatusCard
          status={status}
          agentId={identity.agent_id}
          workspace={identity.workspace_path}
          lastError={lastError}
        />
      )}
    </div>
  );
}

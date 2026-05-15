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

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs uppercase tracking-wide text-muted-foreground">Deployment</div>
        <div className="flex items-center gap-2 text-xl font-semibold">
          {status === "deploying" && <Loader2 className="h-4 w-4 animate-spin" />}
          {status === "deploying" ? "Deploying…" : status === "completed" ? "Done" : status === "failed" ? "Failed" : "Connecting…"}
          <span className="text-muted-foreground font-mono text-xs">({id.slice(0, 8)})</span>
        </div>
      </div>
      <div
        ref={scrollRef}
        className="h-[60vh] overflow-auto rounded-md border bg-zinc-950 p-4 font-mono text-xs text-zinc-200 shadow-inner"
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

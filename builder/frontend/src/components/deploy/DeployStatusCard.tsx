"use client";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle } from "lucide-react";
import Link from "next/link";

export function DeployStatusCard({
  status,
  agentId,
  workspace,
  lastError,
}: {
  status: "completed" | "failed";
  agentId: string;
  workspace: string;
  lastError?: string;
}) {
  if (status === "completed") {
    return (
      <div className="card-sentinel p-6 space-y-4">
        <div className="flex items-center gap-2 oc-orange font-semibold">
          <CheckCircle2 className="h-5 w-5" /> Deployment complete
        </div>
        <div className="space-y-1 text-sm">
          <div className="text-muted-foreground">
            Agent ID:{" "}
            <code className="font-mono text-foreground">{agentId}</code>
          </div>
          <div className="text-muted-foreground">
            Workspace:{" "}
            <code className="font-mono text-foreground">{workspace}</code>
          </div>
        </div>
        <div className="space-y-2 rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
          <div className="label-tag mb-2">Next steps</div>
          <ul className="space-y-1.5">
            <li className="flex gap-2">
              <span className="oc-orange shrink-0">→</span>
              If you selected Telegram, run{" "}
              <code className="font-mono text-xs">openclaw channels start telegram</code>{" "}
              on the VPS and follow the bot-token prompt.
            </li>
            <li className="flex gap-2">
              <span className="oc-orange shrink-0">→</span>
              If you selected WhatsApp, run{" "}
              <code className="font-mono text-xs">openclaw channels start whatsapp</code>{" "}
              and scan the QR.
            </li>
            <li className="flex gap-2">
              <span className="oc-orange shrink-0">→</span>
              Send your agent a first message to wake it up.
            </li>
          </ul>
        </div>
        <Button asChild>
          <Link href="/">Back to wizard</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="card-sentinel p-6 space-y-4">
      <div className="flex items-center gap-2 text-destructive font-semibold">
        <XCircle className="h-5 w-5" /> Deployment failed
      </div>
      {lastError && (
        <pre className="rounded-lg border border-border bg-muted/40 p-3 text-xs text-muted-foreground whitespace-pre-wrap">
          {lastError}
        </pre>
      )}
      <Button variant="outline" asChild>
        <Link href="/">Back to wizard</Link>
      </Button>
    </div>
  );
}

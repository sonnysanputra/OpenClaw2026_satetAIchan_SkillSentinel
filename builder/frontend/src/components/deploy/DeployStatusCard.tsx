"use client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
      <Card>
        <CardContent className="space-y-3 pt-6">
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="h-5 w-5" /> <span className="font-medium">Deployment complete</span>
          </div>
          <div className="text-sm">
            <div>
              Agent ID: <code className="font-mono">{agentId}</code>
            </div>
            <div>
              Workspace: <code className="font-mono">{workspace}</code>
            </div>
          </div>
          <div className="text-sm text-muted-foreground">
            <div className="mb-1 font-medium text-foreground">Next manual steps:</div>
            <ul className="list-inside list-disc space-y-1">
              <li>If you selected Telegram, run <code>openclaw channels start telegram</code> on the VPS and follow the bot-token prompt.</li>
              <li>If you selected WhatsApp, run <code>openclaw channels start whatsapp</code> and scan the QR.</li>
              <li>Send your agent a first message to wake it up.</li>
            </ul>
          </div>
          <Button asChild><Link href="/">Back to wizard</Link></Button>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-center gap-2 text-destructive">
          <XCircle className="h-5 w-5" /> <span className="font-medium">Deployment failed</span>
        </div>
        {lastError && <pre className="rounded bg-muted p-2 text-xs whitespace-pre-wrap">{lastError}</pre>}
        <Button asChild variant="outline"><Link href="/">Back to wizard</Link></Button>
      </CardContent>
    </Card>
  );
}

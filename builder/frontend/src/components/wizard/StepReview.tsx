"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useWizard } from "@/store/wizard";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { previewFiles, startDeploy } from "@/lib/api";
import type { DeployRequest, FilePreviewResponse, SkillItem } from "@/types";
import { Loader2, Rocket, Copy, Check } from "lucide-react";

function buildDeployRequest(s: ReturnType<typeof useWizard.getState>): DeployRequest {
  return {
    vps: s.vps,
    identity: s.identity,
    persona: s.persona,
    user_context: s.user_context,
    instructions: s.instructions,
    model: s.model,
    channels: s.channels,
    skills: s.skills
      .filter((sk) => sk.security_status === "approved" || sk.security_status === "overridden")
      .map((sk) => ({
        id: sk.id,
        name: sk.name,
        raw_url: sk.raw_url,
        security_status: sk.security_status as "approved" | "overridden",
        security_reason: sk.security_reason,
      })),
  };
}

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      size="sm"
      variant="outline"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}

export function StepReview() {
  const router = useRouter();
  const state = useWizard();
  const [preview, setPreview] = useState<FilePreviewResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [previewErr, setPreviewErr] = useState<string | null>(null);

  async function loadPreview() {
    setLoadingPreview(true);
    setPreviewErr(null);
    try {
      setPreview(await previewFiles(buildDeployRequest(state)));
    } catch (e: any) {
      setPreviewErr(e?.response?.data?.detail || e?.message || "Could not render preview");
    } finally {
      setLoadingPreview(false);
    }
  }

  async function onDeploy() {
    setDeploying(true);
    try {
      const { session_id } = await startDeploy(buildDeployRequest(state));
      router.push(`/deploy/${session_id}`);
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || "Deploy failed to start");
      setDeploying(false);
    }
  }

  const blockedSkills = state.skills.filter((s: SkillItem) => s.security_status === "blocked");
  const ready =
    state.identity.agent_id &&
    state.vps.host &&
    state.instructions.responsibilities &&
    state.model.model &&
    blockedSkills.length === 0;

  return (
    <div className="space-y-5">
      <div>
        <p className="label-tag">Final check</p>
        <h2 className="text-xl font-extrabold tracking-tight">Review & deploy</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Confirm the summary, preview generated files, then ship it.
        </p>
      </div>

      {/* Summary grid */}
      <div className="card-sentinel p-5 space-y-1">
        <p className="label-tag mb-3">Configuration summary</p>
        <div className="grid gap-y-2 gap-x-6 sm:grid-cols-2 text-sm">
          <Row k="Agent">
            <span className="font-semibold">
              {state.identity.emoji} {state.identity.agent_name}{" "}
              <span className="text-muted-foreground font-mono text-xs">
                ({state.identity.agent_id})
              </span>
            </span>
          </Row>
          <Row k="VPS">
            {state.vps.user}@{state.vps.host}:{state.vps.port}
          </Row>
          <Row k="Model">
            {state.model.provider}/{state.model.model}
          </Row>
          <Row k="Persona">
            {state.persona.tone}, {state.persona.traits.join(", ") || "—"}
          </Row>
          <Row k="Channels">
            {state.channels.selected.join(", ") || "none"}
          </Row>
          <Row k="Skills">
            {state.skills.length === 0
              ? "none"
              : `${state.skills.filter((s) => s.security_status === "approved").length} approved · ${state.skills.filter((s) => s.security_status === "overridden").length} overridden${blockedSkills.length ? ` · ${blockedSkills.length} BLOCKED` : ""}`}
          </Row>
        </div>
        {blockedSkills.length > 0 && (
          <div className="mt-3">
            <Badge variant="destructive">
              {blockedSkills.length} blocked skill(s) must be removed or overridden before deploy
            </Badge>
          </div>
        )}
      </div>

      {/* File preview */}
      <div className="card-sentinel p-5 space-y-3">
        <div className="flex items-center justify-between">
          <p className="label-tag">Generated workspace files</p>
          <Button size="sm" variant="outline" onClick={loadPreview} disabled={loadingPreview}>
            {loadingPreview && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Render preview
          </Button>
        </div>
        {previewErr && (
          <div className="text-xs text-destructive">{previewErr}</div>
        )}
        {preview && (
          <Tabs defaultValue="soul" className="w-full">
            <TabsList>
              <TabsTrigger value="soul">SOUL.md</TabsTrigger>
              <TabsTrigger value="user">USER.md</TabsTrigger>
              <TabsTrigger value="agents">AGENTS.md</TabsTrigger>
              <TabsTrigger value="identity">IDENTITY.md</TabsTrigger>
            </TabsList>
            {[
              { key: "soul", val: preview.soul_md },
              { key: "user", val: preview.user_md },
              { key: "agents", val: preview.agents_md },
              { key: "identity", val: preview.identity_md },
            ].map(({ key, val }) => (
              <TabsContent key={key} value={key}>
                <div className="mb-2 flex justify-end">
                  <CopyBtn text={val} />
                </div>
                <pre className="max-h-[400px] overflow-auto rounded-lg border border-border bg-muted/50 p-3 font-mono text-xs text-foreground/80">
                  {val}
                </pre>
              </TabsContent>
            ))}
          </Tabs>
        )}
      </div>

      <div className="flex justify-end">
        <Button size="lg" disabled={!ready || deploying} onClick={onDeploy}>
          {deploying ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Rocket className="h-4 w-4" />
          )}
          {deploying ? "Starting deploy…" : "Deploy agent"}
        </Button>
      </div>
    </div>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="w-20 shrink-0 label-tag">{k}</span>
      <span>{children}</span>
    </div>
  );
}

"use client";
import { useState } from "react";
import { useWizard } from "@/store/wizard";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Badge } from "@/components/ui/badge";
import { testSsh } from "@/lib/api";
import { Loader2 } from "lucide-react";

export function StepVps() {
  const vps = useWizard((s) => s.vps);
  const updateVps = useWizard((s) => s.updateVps);
  const [probing, setProbing] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  async function onTest() {
    setProbing(true);
    setResult(null);
    try {
      const r = await testSsh({
        host: vps.host,
        user: vps.user,
        port: vps.port,
        auth_method: vps.auth_method,
        ssh_private_key: vps.auth_method === "key" ? vps.ssh_private_key : null,
        ssh_password: vps.auth_method === "password" ? vps.ssh_password : null,
      });
      if (r.success) {
        setResult({
          ok: true,
          msg: `Connected · ${r.os || "unknown OS"}${r.openclaw_installed ? " · openclaw already installed" : ""}`,
        });
      } else {
        setResult({ ok: false, msg: r.error || "Connection failed" });
      }
    } catch (e: any) {
      setResult({ ok: false, msg: e?.message || "Network error" });
    } finally {
      setProbing(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">VPS access</h2>
        <p className="text-sm text-muted-foreground">
          Where should we install your new OpenClaw agent?
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr]">
        <div>
          <Label htmlFor="host">Host or IP</Label>
          <Input id="host" placeholder="123.45.67.89" value={vps.host} onChange={(e) => updateVps({ host: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="user">User</Label>
          <Input id="user" value={vps.user} onChange={(e) => updateVps({ user: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="port">Port</Label>
          <Input
            id="port"
            type="number"
            value={vps.port}
            onChange={(e) => updateVps({ port: Number(e.target.value) || 22 })}
          />
        </div>
      </div>

      <div>
        <Label>Authentication</Label>
        <RadioGroup
          className="mt-2 flex gap-4"
          value={vps.auth_method}
          onValueChange={(v) => updateVps({ auth_method: v as "key" | "password" })}
        >
          <label className="flex items-center gap-2 text-sm">
            <RadioGroupItem value="key" id="auth-key" /> SSH key
          </label>
          <label className="flex items-center gap-2 text-sm">
            <RadioGroupItem value="password" id="auth-pw" /> Password
          </label>
        </RadioGroup>
      </div>

      {vps.auth_method === "key" ? (
        <div>
          <Label htmlFor="key">Private key (PEM)</Label>
          <Textarea
            id="key"
            className="font-mono text-xs"
            rows={6}
            placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
            value={vps.ssh_private_key}
            onChange={(e) => updateVps({ ssh_private_key: e.target.value })}
          />
        </div>
      ) : (
        <div>
          <Label htmlFor="pw">Password</Label>
          <Input id="pw" type="password" value={vps.ssh_password} onChange={(e) => updateVps({ ssh_password: e.target.value })} />
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button type="button" variant="secondary" onClick={onTest} disabled={probing || !vps.host}>
          {probing ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Test connection
        </Button>
        {result && (
          <Badge variant={result.ok ? "success" : "destructive"} className="font-normal">
            {result.msg}
          </Badge>
        )}
      </div>
    </div>
  );
}

export function validateVps(s: ReturnType<typeof useWizard.getState>): boolean {
  const v = s.vps;
  if (!v.host || !v.user || !v.port) return false;
  if (v.auth_method === "key" && !v.ssh_private_key) return false;
  if (v.auth_method === "password" && !v.ssh_password) return false;
  return true;
}

---
name: skillsentinel-dynamic
description: "Sandboxed runtime behavior analysis for AI agent skills. Runs the skill's entrypoint inside firejail with deny-all network, read-only filesystem, and a honeypot $HOME seeded with decoy credentials. Emits findings for credential reads, blocked egress, persistence writes, and CPU saturation. Fourth specialist in the SkillSentinel multi-agent security scanner."
metadata:
  openclaw:
    emoji: "🧪"
    requires:
      bins: ["python3", "firejail"]
---

# SkillSentinel Dynamic

The behavioral analyzer of SkillSentinel — runs the bundle's entrypoint in a
sandbox with decoy credentials and observes what it tries to do.

## When to Use

- After Intake + Static have given the bundle a clean structural pass but you
  want to confirm runtime behavior.
- For bundles flagged as suspicious by Semantic — Dynamic provides the
  smoking-gun evidence of credential exfiltration or persistence attempts.
- As part of the full multi-agent SkillSentinel pipeline.

## What It Does

Runs `python3 <entrypoint>` inside **firejail** with:
- `--net=none` — no network at all (any outbound attempt fails)
- `--read-only=/` — filesystem is read-only outside the bundle dir
- Fake `$HOME` with decoy credential files (`~/.ssh/id_rsa`, `~/.aws/credentials`,
  `~/.config/openclaw/auth.json`, `~/.env`) — all containing obvious-fake content
- Pre-seeded persistence file decoys (`.bashrc`, `.profile`, systemd units) as
  read-only (writes fail with EROFS)
- 15s wall-clock + 256MB memory + 5-process limits

Findings emerge from three signals:
1. **Decoy file access** (atime advanced) → `READ_CREDENTIAL_FILE` (CRITICAL)
2. **Stderr pattern matching** for "Network is unreachable", "Read-only file system",
   `getaddrinfo`, `/proc/1/cgroup` → `EGRESS_TO_UNDECLARED_HOST`,
   `WRITE_PERSISTENCE_LOCATION`, `DNS_TUNNEL_SUSPECT`, `SANDBOX_DETECTION_ATTEMPT`
3. **Wall-clock saturation** (ran for ≥85% of the budget) → `CRYPTO_MINER_SUSPECT`

## How To Run

```bash
dynamic.py <path-to-bundle>
```

Outputs a structured JSON report on stdout. Broadcasts start + result to
Discord via webhook (env var `SKILLSENTINEL_DISCORD_WEBHOOK`).

## Requirements

- `firejail` installed on host (`apt install firejail`)
- Python 3.10+
- `SKILLSENTINEL_DISCORD_WEBHOOK` env var for Discord narration (optional —
  agent works without it, just no embeds)

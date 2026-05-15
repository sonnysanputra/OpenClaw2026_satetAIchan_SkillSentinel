---
name: skillsentinel-intake
description: "Structural and manifest analysis for AI agent skill bundles. Detects malformed manifests, signature gaps, dependency typosquats, and over-broad capability claims. First specialist in the SkillSentinel multi-agent security scanner."
metadata:
  openclaw:
    emoji: "🛡️"
    requires:
      bins: ["python3"]
---

# SkillSentinel Intake

The structural analyzer of SkillSentinel — the cheapest, fastest pass before the
heavier specialists (Static, Semantic, Dynamic, Verdict) run.

## When to Use

- Before installing any new skill bundle from ClawHub or a third-party registry.
- During incident response after the ClawHavoc malicious-skill incident.
- As part of the full multi-agent SkillSentinel pipeline.

## What It Does

Four checks: manifest validation (required fields, entrypoint exists),
capability breadth (warns if >10 capabilities), signature presence (LOW
finding if missing), dependency coherence (flags imports not in declared
deps — catches typosquat-by-omission).

## How To Run

```bash
intake.py <path-to-bundle>
```

Outputs JSON to stdout. Broadcasts to Discord via webhook
(env var `SKILLSENTINEL_DISCORD_WEBHOOK`).

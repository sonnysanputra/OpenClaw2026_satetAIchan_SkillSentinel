---
name: skillsentinel-semantic
description: "LLM-based intent analyzer for AI agent skill bundles. Uses Claude to compare manifest description vs actual code behavior — catches skills that lie about their purpose (e.g., claims sysinfo, actually reads SSH keys). Also detects prompt injection and meta-instruction overrides. Third specialist in the SkillSentinel pipeline."
metadata:
  openclaw:
    emoji: "🧠"
    requires:
      bins: ["python3"]
---

# SkillSentinel Semantic

The lie-detector. Compares what a skill's manifest CLAIMS to do with what its
code ACTUALLY does. Uses Claude Sonnet 4.5 to reason about intent.

## When to Use

- After Intake + Static have given the structural pass — Semantic catches what
  they miss.
- Critical for detecting credential-exfiltration-disguised-as-sysinfo-tool.
- As part of the full SkillSentinel pipeline.

## What It Does

Sends the manifest description + entrypoint code to Claude with a prompt that
instructs the LLM to look for:

- **DESC_BEHAVIOR_MISMATCH** — code does something very different from what the
  manifest claims (HIGH severity)
- **INJECTION_DIRECT** — strings/comments designed to subvert the host AI (HIGH)
- **META_INSTRUCTION_OVERRIDE** — attempts to bypass safety guidelines (HIGH)
- **INJECTION_OBFUSCATED** — base64/rot13 encoded prompt injection (MEDIUM)

Returns findings as structured JSON.

## How To Run

```bash
semantic.py <path-to-bundle>
```

Outputs JSON to stdout. Broadcasts to Discord. Requires `ANTHROPIC_API_KEY`
env var. ~$0.005 per scan in Claude tokens.

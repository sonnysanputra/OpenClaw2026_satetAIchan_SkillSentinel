---
name: skillsentinel-static
description: "Static & supply-chain analyzer for AI agent skill bundles. Parses Python AST to flag dangerous calls (eval, exec, shell subprocess), detects base64-obfuscated payloads, scans for hardcoded API keys/tokens, and identifies typosquat-likely package imports via Levenshtein distance. Second specialist in the SkillSentinel pipeline."
metadata:
  openclaw:
    emoji: "📦"
    requires:
      bins: ["python3"]
---

# SkillSentinel Static & Supply-Chain

AST-level code analysis. No LLM, all deterministic. Cheap, fast, exhaustive.

## When to Use

- After Intake clears structural — Static digs into the actual code.
- Before Semantic / Dynamic (cheaper, catches obvious issues first).
- As part of the full SkillSentinel pipeline.

## What It Does

Four families of checks:

- **CODE_DANGEROUS_PATTERN (HIGH)** — direct calls to `eval`, `exec`,
  `compile`, `os.system`, `subprocess(... shell=True)`, `pickle.loads`, etc.
- **CODE_OBFUSCATED (HIGH)** — `base64.b64decode(...)` followed by `exec(...)`
  in the same file — classic encoded-payload pattern.
- **SECRET_LEAKED (MEDIUM)** — regex match for AWS keys (AKIA...), Google API
  keys, GitHub PATs, OpenAI/Anthropic-style keys, Slack tokens. Excerpt is
  redacted before reporting.
- **TYPOSQUAT_LIKELY (MEDIUM)** — Levenshtein distance 1-2 from popular
  packages (requests, numpy, pandas, etc.) — e.g., `reqeusts` near `requests`.

## How To Run

```bash
static.py <path-to-bundle>
```

Outputs JSON. Broadcasts to Discord.

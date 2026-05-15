---
name: skillsentinel-verdict
description: "Final adjudicator for AI agent skill bundles. Aggregates findings from Intake, Static, Semantic, and Dynamic agents into a single signed RiskReport with risk score (0-100) and verdict (ALLOW/WARN/REVIEW/BLOCK). Pure deterministic scoring — no LLM. Fifth and final specialist in the SkillSentinel pipeline."
metadata:
  openclaw:
    emoji: "⚖️"
    requires:
      bins: ["python3"]
---

# SkillSentinel Verdict

The final adjudicator. Integrates findings from upstream agents into one signed
decision: ALLOW, WARN, REVIEW, or BLOCK.

## When to Use

- After Intake, Static, Semantic, and Dynamic have produced findings.
- As the closing step of a SkillSentinel scan pipeline.
- Standalone: invoking verdict re-runs Intake + Dynamic to produce a complete
  decision even without the other specialists.

## What It Does

Pure deterministic scoring (no LLM, for auditability). Aggregates findings via:

- Severity weights: INFO=0, LOW=5, MEDIUM=15, HIGH=35, CRITICAL=60
- Category multipliers: READ_CREDENTIAL_FILE x2.0, INJECTION_DIRECT x1.8,
  DESC_BEHAVIOR_MISMATCH x1.5, WRITE_PERSISTENCE x1.3, EGRESS x1.3, else x1.0
- risk_score = clamp(sum over findings of severity * confidence * multiplier, 0, 100)

Thresholds:
- 0-19: ALLOW
- 20-49: WARN
- 50-79: REVIEW
- 80-100: BLOCK

## How To Run

```bash
verdict.py <path-to-bundle>
```

Outputs a structured JSON RiskReport on stdout. Broadcasts the final verdict
to Discord via webhook with risk score, confidence, policy hash, and
justification.

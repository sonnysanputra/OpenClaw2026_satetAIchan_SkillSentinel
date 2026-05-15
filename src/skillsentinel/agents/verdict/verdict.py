"""Agent 5 — Verdict.

**Modality:** adjudicative.
**Question answered:** "Given all the evidence, what is the verdict, what does
the user see, and what happens next?"

Subroutines (to be implemented in Phase 3):

* Policy compliance via OPA / Rego.
* Weighted risk synthesis with hard-veto rules on ``CRITICAL`` findings.
* LLM-generated justification citing specific finding IDs.
* Ed25519 verdict signing.
* SBOM emission (CycloneDX).
* Continuous-monitor subscription.

Phase-0 stub: applies a simple heuristic so the end-to-end pipeline produces a
plausible verdict.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from skillsentinel.shared import Finding, RiskReport, Severity, SkillBundle, Verdict

log = logging.getLogger(__name__)


# Phase-0 heuristic weights. Phase 3 replaces these with policy-driven scoring.
_SEVERITY_WEIGHT: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 5,
    Severity.MEDIUM: 15,
    Severity.HIGH: 30,
    Severity.CRITICAL: 60,
}


class VerdictAgent:
    """Phase-0 stub. Phase-3 will add OPA, signing, SBOM, monitoring."""

    async def run(self, bundle: SkillBundle, findings: list[Finding]) -> RiskReport:
        """Fuse findings into a verdict."""
        score = _score(findings)
        verdict = _bucket(score, findings)
        justification = _justify(verdict, findings)

        report = RiskReport(
            bundle_sha=bundle.bundle_sha,
            verdict=verdict,
            risk_score=score,
            confidence=0.5,  # Phase-0 placeholder
            findings=findings,
            justification=justification,
            policy_name="default",
            policy_hash=_dummy_policy_hash(),
            scanned_at=datetime.now(timezone.utc),
            scanner_deployment_id="dev-local",
            signature=None,  # Signing arrives in Phase 3.
        )

        log.info(
            "verdict.emitted",
            extra={"bundle_sha": bundle.bundle_sha, "verdict": verdict.value, "score": score},
        )
        return report


def _score(findings: list[Finding]) -> int:
    total = sum(int(_SEVERITY_WEIGHT[f.severity] * f.confidence) for f in findings)
    return min(100, total)


def _bucket(score: int, findings: list[Finding]) -> Verdict:
    if any(f.severity is Severity.CRITICAL for f in findings):
        return Verdict.BLOCK
    if score >= 60:
        return Verdict.REVIEW
    if score >= 25:
        return Verdict.WARN
    return Verdict.ALLOW


def _justify(verdict: Verdict, findings: list[Finding]) -> str:
    if not findings:
        return "No findings detected. (Phase-0 stub — agents not yet implemented.)"
    top = sorted(findings, key=lambda f: (-_SEVERITY_WEIGHT[f.severity], -f.confidence))[:3]
    pieces = [f"{f.severity.value} {f.category.value} ({f.id})" for f in top]
    return f"Verdict {verdict.value}. Top findings: {'; '.join(pieces)}."


def _dummy_policy_hash() -> str:
    return hashlib.sha256(b"default-policy-v0").hexdigest()

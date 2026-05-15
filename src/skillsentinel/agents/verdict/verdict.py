"""Agent 5 — Verdict (adjudicator).

The final adjudicator in the SkillSentinel pipeline. Takes findings from
upstream agents (Intake, Static, Semantic, Dynamic) and renders a single
decision: ALLOW / WARN / REVIEW / BLOCK.

No LLM. Pure deterministic scoring. This is by design — verdict logic must
be auditable, version-controllable, and reproducible (same findings -> same
verdict, always). The smart parts are upstream; Verdict just integrates.

Scoring model:
    risk_score = sum over findings of:  severity_weight * confidence * category_weight
    risk_score is clamped to 0-100

Severity weights:
    INFO     = 0
    LOW      = 5
    MEDIUM   = 15
    HIGH     = 35
    CRITICAL = 60

Category weights (multipliers applied to severity_weight):
    Most categories: 1.0
    READ_CREDENTIAL_FILE: 2.0   -- credential exfil is the worst outcome
    INJECTION_DIRECT: 1.8       -- prompt injection severely affects host AI
    DESC_BEHAVIOR_MISMATCH: 1.5 -- skill is actively lying to user

Verdict thresholds:
    risk_score <  20 = ALLOW
    risk_score <  50 = WARN
    risk_score <  80 = REVIEW
    risk_score >= 80 = BLOCK

A single CRITICAL finding alone produces risk >= 60 -> REVIEW.
Two CRITICAL findings -> BLOCK.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from skillsentinel.shared.schemas import (
    Finding,
    FindingCategory,
    RiskReport,
    Severity,
    Verdict,
)

if TYPE_CHECKING:
    from skillsentinel.shared import SkillBundle

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scoring tables (auditable, version-controllable)
# ---------------------------------------------------------------------------

SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.INFO: 0.0,
    Severity.LOW: 5.0,
    Severity.MEDIUM: 15.0,
    Severity.HIGH: 35.0,
    Severity.CRITICAL: 60.0,
}

# Categories where a single finding should count for more than its raw
# severity would imply. Credential exfiltration is the worst possible
# outcome for a skill, so we double the weight.
CATEGORY_MULTIPLIERS: dict[FindingCategory, float] = {
    FindingCategory.READ_CREDENTIAL_FILE: 2.0,
    FindingCategory.INJECTION_DIRECT: 1.8,
    FindingCategory.DESC_BEHAVIOR_MISMATCH: 1.5,
    FindingCategory.WRITE_PERSISTENCE_LOCATION: 1.3,
    FindingCategory.EGRESS_TO_UNDECLARED_HOST: 1.3,
}

# Thresholds (inclusive lower bound) -> Verdict
VERDICT_THRESHOLDS: tuple[tuple[int, Verdict], ...] = (
    (80, Verdict.BLOCK),
    (50, Verdict.REVIEW),
    (20, Verdict.WARN),
    (0,  Verdict.ALLOW),
)

# A placeholder policy hash. In production this would be the SHA-256 of the
# policy bundle in effect; for hackathon we hash our scoring tables.
POLICY_NAME = "default"


def _policy_hash() -> str:
    """SHA-256 of the scoring tables, so the report ties to a specific policy
    version. Any change to weights or thresholds changes this hash."""
    payload = json.dumps(
        {
            "severity": {k.value: v for k, v in SEVERITY_WEIGHTS.items()},
            "category_multipliers": {k.value: v for k, v in CATEGORY_MULTIPLIERS.items()},
            "thresholds": [(t, v.value) for t, v in VERDICT_THRESHOLDS],
        },
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _score_finding(f: Finding) -> float:
    """Return the risk points this finding contributes."""
    base = SEVERITY_WEIGHTS.get(f.severity, 0.0)
    mult = CATEGORY_MULTIPLIERS.get(f.category, 1.0)
    return base * f.confidence * mult


def _verdict_for(risk_score: int) -> Verdict:
    """Map an integer risk score (0-100) to a Verdict."""
    for threshold, verdict in VERDICT_THRESHOLDS:
        if risk_score >= threshold:
            return verdict
    return Verdict.ALLOW


def _justification(
    bundle: "SkillBundle",
    findings: list[Finding],
    risk_score: int,
    verdict: Verdict,
) -> str:
    """One-sentence human-readable explanation of the verdict."""
    if not findings:
        return (
            f"No findings emitted by any agent. "
            f"{bundle.name} v{bundle.version} cleared all checks."
        )

    by_severity: dict[Severity, int] = {}
    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

    parts = []
    for sev in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW):
        if sev in by_severity:
            parts.append(f"{by_severity[sev]} {sev.value}")
    severity_summary = ", ".join(parts) if parts else "no notable findings"

    # Surface the worst-category finding for the headline.
    worst = max(findings, key=lambda f: SEVERITY_WEIGHTS.get(f.severity, 0)
                                          * f.confidence
                                          * CATEGORY_MULTIPLIERS.get(f.category, 1.0))

    return (
        f"{verdict.value} (risk {risk_score}/100) on {bundle.name} v{bundle.version}: "
        f"{severity_summary} across {len(findings)} total. "
        f"Headline: [{worst.severity.value}] {worst.category.value} "
        f"(agent: {worst.agent}, confidence: {worst.confidence:.2f})."
    )


class VerdictAgent:
    """Aggregate findings into a signed RiskReport.

    Called by the orchestrator as ``await verdict.run(bundle, findings)``,
    where ``findings`` is the union of every upstream agent's output.
    """

    def __init__(self, *, policy_name: str = POLICY_NAME) -> None:
        self.policy_name = policy_name

    async def run(self, bundle: "SkillBundle", findings: list[Finding]) -> RiskReport:
        log.info(
            "verdict.start",
            extra={"bundle_sha": bundle.bundle_sha, "n_findings": len(findings)},
        )

        # Sum risk points across all findings.
        raw_score = sum(_score_finding(f) for f in findings)

        # Clamp 0-100 and round to int (RiskReport.risk_score is int).
        risk_score = max(0, min(100, int(round(raw_score))))

        verdict = _verdict_for(risk_score)

        # Confidence in the verdict itself: take the mean of finding
        # confidences if any findings exist, otherwise high confidence in
        # the ALLOW.
        if findings:
            mean_conf = sum(f.confidence for f in findings) / len(findings)
            verdict_confidence = round(min(1.0, mean_conf + 0.1), 2)
        else:
            verdict_confidence = 0.95

        report = RiskReport(
            bundle_sha=bundle.bundle_sha,
            verdict=verdict,
            risk_score=risk_score,
            confidence=verdict_confidence,
            findings=list(findings),
            justification=_justification(bundle, findings, risk_score, verdict),
            policy_name=self.policy_name,
            policy_hash=_policy_hash(),
            scanned_at=datetime.now(timezone.utc),
        )

        log.info(
            "verdict.done",
            extra={
                "bundle_sha": bundle.bundle_sha,
                "verdict": verdict.value,
                "risk_score": risk_score,
                "confidence": verdict_confidence,
            },
        )
        return report

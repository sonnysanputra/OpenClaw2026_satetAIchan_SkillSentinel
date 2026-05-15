"""Tests for the shared Pydantic schemas — the contract every agent depends on."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from skillsentinel.shared import (
    Finding,
    FindingCategory,
    RiskReport,
    Severity,
    SkillBundle,
    Verdict,
)
from skillsentinel.shared.schemas import EvidencePointer, SkillFile

VALID_SHA = "a" * 64


# ----------------------------------------------------------------------------
# SkillFile
# ----------------------------------------------------------------------------
def test_skill_file_round_trip() -> None:
    f = SkillFile(path="scripts/run.py", sha256=VALID_SHA, size_bytes=42)
    assert f.path == "scripts/run.py"
    assert SkillFile.model_validate(f.model_dump()) == f


def test_skill_file_rejects_bad_sha() -> None:
    with pytest.raises(ValidationError):
        SkillFile(path="x", sha256="not-a-real-sha", size_bytes=0)


# ----------------------------------------------------------------------------
# SkillBundle
# ----------------------------------------------------------------------------
def test_skill_bundle_minimal() -> None:
    bundle = SkillBundle(
        bundle_sha=VALID_SHA,
        source_format="openclaw",
        name="hello",
        version="1.0.0",
    )
    assert bundle.bundle_sha == VALID_SHA
    assert bundle.findings == []


def test_skill_bundle_round_trip() -> None:
    bundle = SkillBundle(
        bundle_sha=VALID_SHA,
        source_format="claude_code",
        name="x",
        version="2.3.4",
        declared_capabilities=["fs:read", "network:out"],
    )
    restored = SkillBundle.model_validate(bundle.model_dump())
    assert restored == bundle


# ----------------------------------------------------------------------------
# Finding
# ----------------------------------------------------------------------------
def test_finding_minimal() -> None:
    f = Finding(
        id="F-0001",
        agent="static_supply",
        category=FindingCategory.CODE_DANGEROUS_PATTERN,
        severity=Severity.HIGH,
        confidence=0.8,
        message="exec() called with attacker-influenced input",
    )
    assert f.confidence == 0.8
    assert Finding.model_validate(f.model_dump()) == f


def test_finding_with_evidence() -> None:
    ev = EvidencePointer(file_path="run.py", line_start=10, line_end=12, quoted_text="exec(x)")
    f = Finding(
        id="F-0002",
        agent="static_supply",
        category=FindingCategory.CODE_DANGEROUS_PATTERN,
        severity=Severity.CRITICAL,
        confidence=1.0,
        message="exec",
        evidence=ev,
    )
    assert f.evidence is not None
    assert f.evidence.line_start == 10


@pytest.mark.parametrize("bad_confidence", [-0.1, 1.5, 2.0])
def test_finding_confidence_bounds(bad_confidence: float) -> None:
    with pytest.raises(ValidationError):
        Finding(
            id="F-0003",
            agent="semantic",
            category=FindingCategory.INJECTION_DIRECT,
            severity=Severity.LOW,
            confidence=bad_confidence,
            message="x",
        )


# ----------------------------------------------------------------------------
# RiskReport
# ----------------------------------------------------------------------------
def test_risk_report_round_trip() -> None:
    report = RiskReport(
        bundle_sha=VALID_SHA,
        verdict=Verdict.WARN,
        risk_score=42,
        confidence=0.7,
        findings=[],
        justification="stub",
        policy_name="default",
        policy_hash="b" * 64,
        scanned_at=datetime.now(timezone.utc),
    )
    restored = RiskReport.model_validate(report.model_dump(mode="json"))
    assert restored.verdict is Verdict.WARN
    assert restored.risk_score == 42


def test_risk_report_score_bounds() -> None:
    with pytest.raises(ValidationError):
        RiskReport(
            bundle_sha=VALID_SHA,
            verdict=Verdict.ALLOW,
            risk_score=150,  # out of range
            confidence=0.5,
            findings=[],
            justification="x",
            policy_name="default",
            policy_hash="c" * 64,
            scanned_at=datetime.now(timezone.utc),
        )


def test_risk_report_naive_datetime_is_coerced_to_utc() -> None:
    report = RiskReport(
        bundle_sha=VALID_SHA,
        verdict=Verdict.ALLOW,
        risk_score=0,
        confidence=0.5,
        findings=[],
        justification="x",
        policy_name="default",
        policy_hash="d" * 64,
        scanned_at=datetime(2026, 1, 1, 0, 0, 0),  # noqa: DTZ001 — exercising the coercer
    )
    assert report.scanned_at.tzinfo == timezone.utc

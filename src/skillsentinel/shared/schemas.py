"""Core data contracts used by every agent.

These types are the *only* thing shared across agent boundaries. Every agent
emits ``Finding`` objects with severity/confidence/evidence pointers; the
orchestrator aggregates them; the verdict agent fuses them into a ``RiskReport``.

Keeping the contract tiny is deliberate: the smaller this file is, the easier
it is to evolve agents in parallel without breaking each other.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ----------------------------------------------------------------------------
# Enums
# ----------------------------------------------------------------------------
class Severity(str, Enum):
    """Severity of a single Finding."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Verdict(str, Enum):
    """Final verdict on a skill bundle."""

    ALLOW = "ALLOW"
    WARN = "WARN"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class FindingCategory(str, Enum):
    """Closed taxonomy of finding categories.

    Add new values here as you implement new detectors. Keeping this enum
    closed (rather than free-text) is what lets the Verdict agent reason
    mechanically about findings.
    """

    # Agent 1 — Intake
    MANIFEST_INVALID = "MANIFEST_INVALID"
    MANIFEST_OVER_BROAD = "MANIFEST_OVER_BROAD"
    SIGNATURE_MISSING = "SIGNATURE_MISSING"
    DEPENDENCY_UNDECLARED = "DEPENDENCY_UNDECLARED"

    # Agent 2 — Static & Supply-Chain
    CODE_DANGEROUS_PATTERN = "CODE_DANGEROUS_PATTERN"
    CODE_OBFUSCATED = "CODE_OBFUSCATED"
    SECRET_LEAKED = "SECRET_LEAKED"
    CVE_HIGH = "CVE_HIGH"
    TYPOSQUAT_LIKELY = "TYPOSQUAT_LIKELY"
    IOC_KNOWN_BAD = "IOC_KNOWN_BAD"
    PUBLISHER_NEW = "PUBLISHER_NEW"
    KEY_ROTATION_UNVERIFIED = "KEY_ROTATION_UNVERIFIED"
    VERSION_VELOCITY_ANOMALY = "VERSION_VELOCITY_ANOMALY"

    # Agent 3 — Semantic (LLM)
    INJECTION_DIRECT = "INJECTION_DIRECT"
    INJECTION_OBFUSCATED = "INJECTION_OBFUSCATED"
    META_INSTRUCTION_OVERRIDE = "META_INSTRUCTION_OVERRIDE"
    DESC_BEHAVIOR_MISMATCH = "DESC_BEHAVIOR_MISMATCH"

    # Agent 4 — Dynamic
    EGRESS_TO_UNDECLARED_HOST = "EGRESS_TO_UNDECLARED_HOST"
    DNS_TUNNEL_SUSPECT = "DNS_TUNNEL_SUSPECT"
    BEACON_PATTERN = "BEACON_PATTERN"
    READ_CREDENTIAL_FILE = "READ_CREDENTIAL_FILE"
    WRITE_PERSISTENCE_LOCATION = "WRITE_PERSISTENCE_LOCATION"
    CRYPTO_MINER_SUSPECT = "CRYPTO_MINER_SUSPECT"
    FORK_BOMB = "FORK_BOMB"
    SANDBOX_DETECTION_ATTEMPT = "SANDBOX_DETECTION_ATTEMPT"

    # Agent 5 — Verdict / policy
    POLICY_VIOLATION = "POLICY_VIOLATION"


# ----------------------------------------------------------------------------
# Skill bundle
# ----------------------------------------------------------------------------
class SkillFile(BaseModel):
    """One file inside a skill bundle."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(description="Relative path within the bundle.")
    sha256: str = Field(description="Hex-encoded SHA-256 of the file contents.")
    size_bytes: int = Field(ge=0)
    mime_type: str | None = None

    @field_validator("sha256")
    @classmethod
    def _validate_sha(cls, v: str) -> str:
        if len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            msg = "sha256 must be a 64-char hex string"
            raise ValueError(msg)
        return v.lower()


class SkillBundle(BaseModel):
    """The canonical, host-agnostic representation of a skill being scanned.

    Each parser (OpenClaw, Claude Code, MCP, …) produces one of these. Every
    downstream agent reads only from this representation.
    """

    model_config = ConfigDict(frozen=True)

    bundle_sha: str = Field(description="SHA-256 of the bundle archive.")
    source_format: Literal["openclaw", "claude_code", "mcp", "openai_plugin", "unknown"]
    name: str
    version: str
    publisher: str | None = None
    declared_description: str | None = None
    declared_capabilities: list[str] = Field(default_factory=list)
    declared_dependencies: list[str] = Field(default_factory=list)
    files: list[SkillFile] = Field(default_factory=list)
    root_path: Path | None = Field(default=None, exclude=True)
    findings: list[Finding] = Field(default_factory=list)

    @field_validator("bundle_sha")
    @classmethod
    def _validate_bundle_sha(cls, v: str) -> str:
        if len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            msg = "bundle_sha must be a 64-char hex string"
            raise ValueError(msg)
        return v.lower()


# ----------------------------------------------------------------------------
# Findings
# ----------------------------------------------------------------------------
class EvidencePointer(BaseModel):
    """Concrete pointer to where in the bundle a finding originates.

    Verdict justifications cite these. Required for explainability.
    """

    model_config = ConfigDict(frozen=True)

    file_path: str | None = None
    line_start: int | None = Field(default=None, ge=0)
    line_end: int | None = Field(default=None, ge=0)
    byte_offset: int | None = Field(default=None, ge=0)
    trace_id: str | None = None
    quoted_text: str | None = None


class Finding(BaseModel):
    """A single discrete observation produced by one agent."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique within a single scan, e.g. 'F-0014'.")
    agent: Literal["intake", "static_supply", "semantic", "dynamic", "verdict"]
    category: FindingCategory
    severity: Severity
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    message: str
    evidence: EvidencePointer | None = None
    extra: dict[str, str] = Field(default_factory=dict)


# Forward-reference resolution for SkillBundle.findings
SkillBundle.model_rebuild()


# ----------------------------------------------------------------------------
# Scan request / response
# ----------------------------------------------------------------------------
class ScanRequest(BaseModel):
    """Inbound request to scan a bundle."""

    bundle_path: Path
    policy_name: str = "default"
    enable_dynamic: bool = True
    timeout_seconds: int = Field(default=120, ge=1, le=900)
    requester: str | None = None


class ScanResponse(BaseModel):
    """High-level response shape returned by the orchestrator."""

    report: RiskReport
    cache_hit: bool = False


# ----------------------------------------------------------------------------
# Risk report (the verdict agent's output)
# ----------------------------------------------------------------------------
class RiskReport(BaseModel):
    """Signed, structured verdict emitted by the Verdict agent."""

    bundle_sha: str
    verdict: Verdict
    risk_score: Annotated[int, Field(ge=0, le=100)]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    findings: list[Finding]
    justification: str
    policy_name: str
    policy_hash: str = Field(description="SHA-256 of the policy bundle in effect.")
    scanned_at: datetime
    scanner_deployment_id: str = Field(
        default="unspecified",
        description=(
            "Opaque ID for the SkillSentinel deployment. Replaces version "
            "in public builds so adversaries cannot fingerprint the scanner."
        ),
    )
    signature: str | None = Field(
        default=None,
        description="Hex-encoded Ed25519 signature over the canonical JSON form.",
    )

    @field_validator("scanned_at", mode="before")
    @classmethod
    def _ensure_utc(cls, v: datetime | str) -> datetime:
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v

"""SkillSentinel orchestrator.

This is deliberately **not** an LLM-driven agent. It is a deterministic workflow
runner. Its job is to:

1. Call Agent 1 (Intake) and wait.
2. Launch Agents 2, 3, 4 in parallel and wait for all to complete (or timeout).
3. Hand all findings to Agent 5 (Verdict).
4. Return the signed report.

Determinism is a feature here: security tools must be auditable, and every LLM
call is a potential prompt-injection sink. The five agents are the smart parts;
the orchestrator just wires them up.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from skillsentinel.agents.dynamic import DynamicAgent
from skillsentinel.agents.intake import IntakeAgent
from skillsentinel.agents.semantic import SemanticAgent
from skillsentinel.agents.static_supply import StaticSupplyAgent
from skillsentinel.agents.verdict import VerdictAgent
from skillsentinel.shared import Finding, ScanRequest, ScanResponse, Severity

if TYPE_CHECKING:
    from skillsentinel.shared import SkillBundle

log = logging.getLogger(__name__)


class Orchestrator:
    """Wires five specialist agents into a single end-to-end pipeline."""

    def __init__(
        self,
        *,
        intake: IntakeAgent | None = None,
        static_supply: StaticSupplyAgent | None = None,
        semantic: SemanticAgent | None = None,
        dynamic: DynamicAgent | None = None,
        verdict: VerdictAgent | None = None,
    ) -> None:
        # Allow dependency injection for testing; default to real implementations.
        self.intake = intake or IntakeAgent()
        self.static_supply = static_supply or StaticSupplyAgent()
        self.semantic = semantic or SemanticAgent()
        self.dynamic = dynamic or DynamicAgent()
        self.verdict = verdict or VerdictAgent()

    async def scan(self, request: ScanRequest) -> ScanResponse:
        """Run the full pipeline on a single skill bundle."""
        log.info("scan.start", extra={"path": str(request.bundle_path)})

        # Phase 1 — Intake (single-agent, synchronous).
        bundle = await self.intake.run(request.bundle_path)

        # Early-exit on critical structural findings.
        if _has_critical(bundle.findings):
            report = await self.verdict.run(bundle, list(bundle.findings))
            return ScanResponse(report=report, cache_hit=False)

        # Phase 2 — Static, Semantic, Dynamic in parallel.
        coroutines = [
            self.static_supply.run(bundle),
            self.semantic.run(bundle),
        ]
        if request.enable_dynamic:
            coroutines.append(self.dynamic.run(bundle))

        results: list[list[Finding]] = await asyncio.gather(*coroutines)

        all_findings: list[Finding] = list(bundle.findings)
        for batch in results:
            all_findings.extend(batch)

        # Phase 3 — Verdict.
        report = await self.verdict.run(bundle, all_findings)

        log.info(
            "scan.done",
            extra={
                "bundle_sha": bundle.bundle_sha,
                "verdict": report.verdict.value,
                "risk_score": report.risk_score,
                "n_findings": len(all_findings),
            },
        )
        return ScanResponse(report=report, cache_hit=False)


def _has_critical(findings: list[Finding]) -> bool:
    return any(f.severity is Severity.CRITICAL for f in findings)

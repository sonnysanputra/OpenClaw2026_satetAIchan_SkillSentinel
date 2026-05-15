"""Agent 2 — Static & Supply-Chain.

**Modality:** static.
**Question answered:** "What can we learn about this skill without running it?"

Subroutines (to be implemented in Phase 1):

* Pattern-based code analysis via Semgrep with a custom AI-skill ruleset.
* Language-specific analysis: Bandit, ESLint security plugin, gosec, cargo-audit.
* Secret scanning: trufflehog, gitleaks.
* Dependency audit: OSV.dev + GitHub Advisory + typosquat scoring.
* Publisher reputation: account age, signing-key continuity, version velocity.
* IOC threat intel: VirusTotal, AbuseIPDB, URLhaus, MalwareBazaar.

Phase-0 stub: returns no findings. Replace with real subroutines during Phase 1.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skillsentinel.shared import Finding

if TYPE_CHECKING:
    from skillsentinel.shared import SkillBundle

log = logging.getLogger(__name__)


class StaticSupplyAgent:
    """Phase-0 stub. Phase-1 will add real subroutines."""

    async def run(self, bundle: SkillBundle) -> list[Finding]:
        """Run all static and supply-chain checks. Returns a list of findings."""
        log.debug("static_supply.run", extra={"bundle_sha": bundle.bundle_sha})
        return []

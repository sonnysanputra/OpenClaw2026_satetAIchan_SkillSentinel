"""Agent 3 — Semantic.

**Modality:** semantic (LLM-based).
**Question answered:** "What does the skill *really* do in natural language, and
is anyone trying to hijack the host model through its instructions?"

This is the only fully LLM-driven agent in the pipeline. Single structured-output
call producing:

* Prompt-injection findings (OWASP LLM01).
* Intent inference (English description of actual behavior).
* Description-vs-behavior diff against publisher's declared description.

Subroutines (to be implemented in Phase 1):

* Deterministic regex pre-filter for known injection patterns.
* Obfuscation decoder pipeline: zero-width, base64, ROT13, RTL, leetspeak.
* Structured-output prompt with concrete evidence pointers.
* Cheap Haiku triage; escalate to Sonnet on suspicious bundles.

Phase-0 stub: returns no findings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skillsentinel.shared import Finding

if TYPE_CHECKING:
    from skillsentinel.shared import SkillBundle

log = logging.getLogger(__name__)


class SemanticAgent:
    """Phase-0 stub. Phase-1 will add real LLM-driven analysis."""

    def __init__(
        self,
        *,
        triage_model: str = "claude-haiku-4-5",
        escalate_model: str = "claude-sonnet-4-6",
    ) -> None:
        self.triage_model = triage_model
        self.escalate_model = escalate_model

    async def run(self, bundle: SkillBundle) -> list[Finding]:
        """Run semantic analysis on the bundle. Returns findings."""
        log.debug("semantic.run", extra={"bundle_sha": bundle.bundle_sha})
        return []

"""Agent 4 — Dynamic Behavior.

**Modality:** dynamic.
**Question answered:** "What does the skill actually do when executed under
realistic conditions?"

Subroutines (to be implemented in Phase 2):

* Sandbox provisioning (gVisor / Firecracker microVM).
* Decoy environment (fake credentials, MCP tokens).
* Randomised fingerprint to defeat sandbox detection.
* Driver LLM that exercises declared tools with synthetic prompts.
* eBPF syscall + filesystem tracing.
* mitmproxy + tcpdump network capture.
* Anti-evasion: clock-skew runs (+30 days), multi-profile runs.
* Behavior classifier translating traces to ``Finding``s.

Phase-0 stub: returns no findings. The most engineering-heavy agent;
allocate a dedicated owner.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skillsentinel.shared import Finding

if TYPE_CHECKING:
    from skillsentinel.shared import SkillBundle

log = logging.getLogger(__name__)


class DynamicAgent:
    """Phase-0 stub. Phase-2 will add the sandbox stack."""

    def __init__(
        self,
        *,
        runtime: str = "gvisor",
        clock_skew_days: int = 30,
        profiles: tuple[str, ...] = ("default", "alice", "root"),
    ) -> None:
        self.runtime = runtime
        self.clock_skew_days = clock_skew_days
        self.profiles = profiles

    async def run(self, bundle: SkillBundle) -> list[Finding]:
        """Run the skill inside a sandbox and analyze its behavior."""
        log.debug("dynamic.run", extra={"bundle_sha": bundle.bundle_sha})
        return []

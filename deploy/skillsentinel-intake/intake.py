#!/opt/skillsentinel/.venv/bin/python3
"""OpenClaw skill wrapper — invokes SkillSentinel's IntakeAgent.

Real logic lives in /opt/skillsentinel/src/skillsentinel/agents/intake/intake.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/skillsentinel/src")

from skillsentinel.agents.intake import IntakeAgent  # noqa: E402
from skillsentinel.shared.broadcast import broadcast  # noqa: E402


def _verdict_hint(findings) -> str:
    sevs = {f.severity.value for f in findings}
    if "CRITICAL" in sevs:
        return "BLOCK"
    if "HIGH" in sevs:
        return "REVIEW"
    if "MEDIUM" in sevs:
        return "WARN"
    return "ALLOW"


async def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: intake.py <bundle_path>"}), file=sys.stderr)
        return 2

    bundle_path = Path(sys.argv[1]).expanduser().resolve()
    broadcast(
        agent="intake",
        level="INFO",
        message=f"🔍 Scanning `{bundle_path.name}`",
        fields={"path": str(bundle_path)},
    )

    try:
        bundle = await IntakeAgent().run(bundle_path)
    except Exception as exc:  # noqa: BLE001
        broadcast(
            agent="intake",
            level="BLOCK",
            message=f"Intake crashed: {exc}",
            fields={"path": str(bundle_path)},
        )
        print(json.dumps({"error": str(exc), "path": str(bundle_path)}),
              file=sys.stderr)
        return 1

    verdict = _verdict_hint(bundle.findings)
    result = {
        "agent": "intake",
        "bundle_sha": bundle.bundle_sha,
        "name": bundle.name,
        "version": bundle.version,
        "source_format": bundle.source_format,
        "n_files": len(bundle.files),
        "n_findings": len(bundle.findings),
        "verdict_hint": verdict,
        "findings": [
            {"id": f.id, "category": f.category.value, "severity": f.severity.value,
             "confidence": f.confidence, "message": f.message}
            for f in bundle.findings
        ],
    }
    print(json.dumps(result, indent=2))

    broadcast(
        agent="intake",
        level=verdict,
        message=f"Scan complete: **{bundle.name}** v{bundle.version}",
        fields={"bundle_sha": bundle.bundle_sha[:12] + "...",
               "findings": str(len(bundle.findings)),
               "files": str(len(bundle.files)),
               "format": bundle.source_format},
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

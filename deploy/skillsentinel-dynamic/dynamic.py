#!/opt/skillsentinel/.venv/bin/python3
"""OpenClaw skill wrapper — invokes SkillSentinel's DynamicAgent.

Takes a bundle path argument, runs the bundle inside firejail with a honeypot
$HOME, outputs a structured JSON report on stdout, and posts INFO + verdict
embeds to Discord via the broadcast helper.

Real logic lives in /opt/skillsentinel/src/skillsentinel/agents/dynamic/dynamic.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/skillsentinel/src")

from skillsentinel.agents.dynamic import DynamicAgent  # noqa: E402
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
        print(json.dumps({"error": "usage: dynamic.py <bundle_path>"}), file=sys.stderr)
        return 2

    bundle_path = Path(sys.argv[1]).expanduser().resolve()

    broadcast(
        agent="dynamic",
        level="INFO",
        message=f"🧪 Sandboxing `{bundle_path.name}`",
        fields={"path": str(bundle_path)},
    )

    try:
        # We need a SkillBundle to feed DynamicAgent; Intake gives us one.
        bundle = await IntakeAgent().run(bundle_path)
        findings = await DynamicAgent().run(bundle)
    except Exception as exc:  # noqa: BLE001
        broadcast(
            agent="dynamic",
            level="BLOCK",
            message=f"Dynamic crashed: {exc}",
            fields={"path": str(bundle_path)},
        )
        print(json.dumps({"error": str(exc), "path": str(bundle_path)}),
              file=sys.stderr)
        return 1

    verdict = _verdict_hint(findings)
    result = {
        "agent": "dynamic",
        "bundle_sha": bundle.bundle_sha,
        "name": bundle.name,
        "version": bundle.version,
        "n_findings": len(findings),
        "verdict_hint": verdict,
        "findings": [
            {
                "id": f.id,
                "category": f.category.value,
                "severity": f.severity.value,
                "confidence": f.confidence,
                "message": f.message,
            }
            for f in findings
        ],
    }
    print(json.dumps(result, indent=2))

    broadcast(
        agent="dynamic",
        level=verdict,
        message=f"Sandbox complete: **{bundle.name}** v{bundle.version}",
        fields={
            "bundle_sha": bundle.bundle_sha[:12] + "...",
            "findings": str(len(findings)),
            "sandbox": "firejail (--net=none, read-only, honeypot $HOME)",
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

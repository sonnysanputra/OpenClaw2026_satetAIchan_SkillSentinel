#!/opt/skillsentinel/.venv/bin/python3
"""OpenClaw skill wrapper — VerdictAgent (final adjudicator)."""
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/skillsentinel/src")

from skillsentinel.agents.intake import IntakeAgent  # noqa: E402
from skillsentinel.agents.dynamic.dynamic import DynamicAgent  # noqa: E402
from skillsentinel.agents.static_supply.static_supply import StaticSupplyAgent  # noqa: E402
from skillsentinel.agents.verdict.verdict import VerdictAgent  # noqa: E402
from skillsentinel.shared.broadcast import broadcast  # noqa: E402


async def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: verdict.py <bundle_path>"}), file=sys.stderr)
        return 2

    bundle_path = Path(sys.argv[1]).expanduser().resolve()

    broadcast(
        agent="verdict",
        level="INFO",
        message=f"⚖️ Adjudicating `{bundle_path.name}`",
        fields={"path": str(bundle_path)},
    )

    try:
        # Re-run cheap+fast agents so verdict has data to integrate.
        bundle = await IntakeAgent().run(bundle_path)
        static_findings = await StaticSupplyAgent().run(bundle)
        dynamic_findings = await DynamicAgent().run(bundle)
        all_findings = list(bundle.findings) + static_findings + dynamic_findings
        report = await VerdictAgent().run(bundle, all_findings)
    except Exception as exc:  # noqa: BLE001
        broadcast(
            agent="verdict", level="BLOCK",
            message=f"Verdict crashed: {exc}",
            fields={"path": str(bundle_path)},
        )
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    # Output JSON using the SAME field names as other agents' wrappers so
    # the Discord bot's parser works uniformly.
    result = {
        "agent": "verdict",
        "bundle_sha": report.bundle_sha,
        "name": bundle.name,
        "version": bundle.version,
        "n_findings": len(report.findings),
        "verdict_hint": report.verdict.value,     # <-- standard key
        "verdict": report.verdict.value,          # <-- also keep for compat
        "risk_score": report.risk_score,
        "confidence": report.confidence,
        "justification": report.justification,
        "policy_name": report.policy_name,
        "policy_hash": report.policy_hash[:16] + "...",
        "findings": [                              # <-- standard key
            {
                "id": f.id,
                "agent": f.agent,
                "category": f.category.value,
                "severity": f.severity.value,
                "confidence": f.confidence,
                "message": f"[{f.severity.value}] {f.category.value} (from {f.agent}): {f.message[:200]}",
            }
            for f in report.findings
        ],
    }
    print(json.dumps(result, indent=2))

    broadcast(
        agent="verdict",
        level=report.verdict.value,
        message=f"⚖️ **Final verdict: {report.verdict.value}** on {bundle.name} v{bundle.version}",
        fields={
            "risk_score": f"{report.risk_score}/100",
            "confidence": f"{report.confidence:.2f}",
            "findings": str(len(report.findings)),
            "policy": f"{report.policy_name} ({report.policy_hash[:8]}...)",
            "justification": report.justification[:512],
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

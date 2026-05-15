#!/opt/skillsentinel/.venv/bin/python3
"""OpenClaw skill wrapper — StaticSupplyAgent (AST + secrets + typosquats)."""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path

sys.path.insert(0, "/opt/skillsentinel/src")

from skillsentinel.agents.intake import IntakeAgent  # noqa: E402
from skillsentinel.agents.static_supply.static_supply import StaticSupplyAgent  # noqa: E402
from skillsentinel.shared.broadcast import broadcast  # noqa: E402


def _verdict_hint(findings) -> str:
    sevs = {f.severity.value for f in findings}
    if "CRITICAL" in sevs: return "BLOCK"
    if "HIGH" in sevs:     return "REVIEW"
    if "MEDIUM" in sevs:   return "WARN"
    return "ALLOW"


async def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: static.py <bundle_path>"}), file=sys.stderr)
        return 2

    bundle_path = Path(sys.argv[1]).expanduser().resolve()
    broadcast("static", "INFO",
              f"📦 AST-analyzing `{bundle_path.name}`",
              fields={"path": str(bundle_path)})

    try:
        bundle = await IntakeAgent().run(bundle_path)
        findings = await StaticSupplyAgent().run(bundle)
    except Exception as exc:  # noqa: BLE001
        broadcast("static", "BLOCK", f"Static crashed: {exc}",
                  fields={"path": str(bundle_path)})
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    verdict = _verdict_hint(findings)
    result = {
        "agent": "static_supply",
        "bundle_sha": bundle.bundle_sha,
        "name": bundle.name,
        "version": bundle.version,
        "n_findings": len(findings),
        "verdict_hint": verdict,
        "findings": [
            {"id": f.id, "category": f.category.value, "severity": f.severity.value,
             "confidence": f.confidence, "message": f.message}
            for f in findings
        ],
    }
    print(json.dumps(result, indent=2))

    broadcast("static", verdict,
              f"Static analysis complete: **{bundle.name}** v{bundle.version}",
              fields={
                  "bundle_sha": bundle.bundle_sha[:12] + "...",
                  "findings": str(len(findings)),
                  "method": "AST + regex (eval/exec/secrets/typosquats)",
              })
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

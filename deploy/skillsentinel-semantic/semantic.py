#!/opt/skillsentinel/.venv/bin/python3
"""OpenClaw skill wrapper — SemanticAgent (LLM intent analyzer)."""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path

sys.path.insert(0, "/opt/skillsentinel/src")

from skillsentinel.agents.intake import IntakeAgent  # noqa: E402
from skillsentinel.agents.semantic.semantic import SemanticAgent  # noqa: E402
from skillsentinel.shared.broadcast import broadcast  # noqa: E402


def _verdict_hint(findings) -> str:
    sevs = {f.severity.value for f in findings}
    if "CRITICAL" in sevs: return "BLOCK"
    if "HIGH" in sevs:     return "REVIEW"
    if "MEDIUM" in sevs:   return "WARN"
    return "ALLOW"


async def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: semantic.py <bundle_path>"}), file=sys.stderr)
        return 2

    bundle_path = Path(sys.argv[1]).expanduser().resolve()
    broadcast("semantic", "INFO",
              f"🧠 Analyzing intent of `{bundle_path.name}` (Claude)",
              fields={"path": str(bundle_path)})

    try:
        bundle = await IntakeAgent().run(bundle_path)
        findings = await SemanticAgent().run(bundle)
    except Exception as exc:  # noqa: BLE001
        broadcast("semantic", "BLOCK", f"Semantic crashed: {exc}",
                  fields={"path": str(bundle_path)})
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    verdict = _verdict_hint(findings)
    result = {
        "agent": "semantic",
        "bundle_sha": bundle.bundle_sha,
        "name": bundle.name,
        "version": bundle.version,
        "n_findings": len(findings),
        "verdict_hint": verdict,
        "findings": [
            {"id": f.id, "category": f.category.value, "severity": f.severity.value,
             "confidence": f.confidence, "message": f.message,
             "evidence": (f.evidence.quoted_text if f.evidence else None)}
            for f in findings
        ],
    }
    print(json.dumps(result, indent=2))

    broadcast("semantic", verdict,
              f"Intent analysis complete: **{bundle.name}** v{bundle.version}",
              fields={
                  "bundle_sha": bundle.bundle_sha[:12] + "...",
                  "findings": str(len(findings)),
                  "method": "Claude Sonnet 4.5 description-vs-code comparison",
              })
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

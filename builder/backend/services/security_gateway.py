"""SkillSentinel REST client.

Each skill is reviewed by:
1. Fetching its SKILL.md from raw_url.
2. Packing it into an in-memory .tar.gz with a minimal skill.yaml manifest.
3. POSTing the bundle to POST /scan/upload on the configured SkillSentinel instance.
4. Mapping the ScanResult final_verdict to "approved" or "blocked".

Verdict mapping:
  ALLOW  → approved
  WARN   → approved  (justification returned as reason so the UI can surface it)
  REVIEW → blocked
  BLOCK  → blocked
"""
from __future__ import annotations

import asyncio
import io
import logging
import tarfile
from typing import Any

import httpx

from core.config import settings

log = logging.getLogger(__name__)

HTTP_FETCH_TIMEOUT_S = 15
SCAN_TIMEOUT_S = 60


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def review_skills_batch(skills: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Review every skill concurrently; returns [{id, status, reason}, ...]."""
    results = await asyncio.gather(
        *[_review_one(s) for s in skills],
        return_exceptions=True,
    )
    out: list[dict[str, Any]] = []
    for skill, result in zip(skills, results):
        if isinstance(result, Exception):
            log.exception("Unexpected error reviewing skill %s", skill.get("id"))
            out.append({
                "id": skill["id"],
                "status": "blocked",
                "reason": f"Review error: {result}",
            })
        else:
            out.append(result)  # type: ignore[arg-type]
    return out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _review_one(skill: dict[str, str]) -> dict[str, Any]:
    skill_id = skill["id"]
    skill_name = skill.get("name", skill_id)
    raw_url = skill.get("raw_url", "")

    skill_content = skill.get("content") or await _fetch_skill_content(skill_id, raw_url)
    if skill_content is None:
        return {"id": skill_id, "status": "blocked", "reason": "Failed to fetch skill content"}

    bundle = _build_bundle(skill_name, skill_content)

    base_url = settings.security_gateway_url.rstrip("/")
    upload_url = f"{base_url}/scan/upload?skip_dynamic=true"

    try:
        async with httpx.AsyncClient(timeout=SCAN_TIMEOUT_S) as client:
            resp = await client.post(
                upload_url,
                files={"file": (f"{skill_id}.tar.gz", bundle, "application/gzip")},
            )
            resp.raise_for_status()
            scan_result: dict[str, Any] = resp.json()
            log.info("Scan response for %s — status=%s body=%s", skill_id, resp.status_code, scan_result)
    except httpx.HTTPStatusError as e:
        log.warning("Scan HTTP error for %s — %s: %s", skill_id, e.response.status_code, e.response.text[:200])
        return {"id": skill_id, "status": "blocked", "reason": f"Scan API error {e.response.status_code}"}
    except Exception as e:
        log.warning("Scan upload exception for %s — %s", skill_id, e)
        return {"id": skill_id, "status": "blocked", "reason": f"Scan upload failed: {e}"}

    return _map_verdict(skill_id, scan_result)


async def _fetch_skill_content(skill_id: str, raw_url: str) -> str | None:
    if not raw_url:
        log.warning("No raw_url for skill %s", skill_id)
        return None
    try:
        async with httpx.AsyncClient(timeout=HTTP_FETCH_TIMEOUT_S) as client:
            resp = await client.get(raw_url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        log.warning("Failed to fetch skill %s from %s: %s", skill_id, raw_url, e)
        return None


def _build_bundle(name: str, skill_content: str) -> bytes:
    """Pack skill.py + SKILL.md + skill.yaml into an in-memory .tar.gz.

    skill.py is the entrypoint so the semantic and static scanners have real
    code to analyse. If skill_content is already Python (first non-empty line
    starts with a Python keyword), it is used as-is; otherwise it is treated
    as markdown documentation and wrapped in a docstring stub.
    """
    safe_name = name.replace('"', "'")
    manifest = (
        f'name: "{safe_name}"\n'
        f'version: "1.0.0"\n'
        f'description: "{safe_name} skill"\n'
        f'entrypoint: "skill.py"\n'
    )

    first_line = next((l for l in skill_content.splitlines() if l.strip()), "")
    _PYTHON_STARTS = ("import ", "from ", "def ", "class ", '"""', "async ")
    if any(first_line.startswith(p) for p in _PYTHON_STARTS):
        py_content = skill_content
    else:
        py_content = f'"""\n{skill_content}\n"""\n'

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for filename, content in [
            ("skill.py", py_content),
            ("SKILL.md", skill_content),
            ("skill.yaml", manifest),
        ]:
            data = content.encode()
            info = tarfile.TarInfo(name=filename)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _map_verdict(skill_id: str, scan_result: dict[str, Any]) -> dict[str, Any]:
    verdict = (scan_result.get("final_verdict") or "BLOCK").upper()
    justification = scan_result.get("justification") or ""
    risk_score = scan_result.get("risk_score", 100)

    if verdict == "ALLOW":
        return {"id": skill_id, "status": "approved", "reason": None}

    if verdict == "WARN":
        return {
            "id": skill_id,
            "status": "approved",
            "reason": f"Warning (risk {risk_score}/100): {justification}",
        }

    # REVIEW or BLOCK
    return {
        "id": skill_id,
        "status": "blocked",
        "reason": justification or f"Verdict: {verdict} (risk {risk_score}/100)",
    }

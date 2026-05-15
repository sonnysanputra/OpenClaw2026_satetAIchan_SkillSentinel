"""End-to-end smoke test of the orchestrator with real Intake + stub others."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from skillsentinel.orchestrator import Orchestrator
from skillsentinel.shared import ScanRequest


@pytest.fixture()
def clean_bundle(tmp_path: Path) -> Path:
    """A minimal but complete skill bundle that should produce ALLOW."""
    bundle = tmp_path / "hello-skill"
    bundle.mkdir()
    (bundle / "skill.yaml").write_text(
        "name: hello-skill\n"
        "version: 0.0.1\n"
        "description: A friendly hello-world skill.\n"
        "entrypoint: run.py\n",
        encoding="utf-8",
    )
    (bundle / "run.py").write_text("print('hello')\n", encoding="utf-8")
    return bundle


async def test_orchestrator_runs_end_to_end(clean_bundle: Path) -> None:
    orchestrator = Orchestrator()
    response = await orchestrator.scan(
        ScanRequest(bundle_path=clean_bundle, enable_dynamic=False)
    )
    assert response.report is not None
    assert response.report.bundle_sha
    # Verdict may be ALLOW or WARN depending on minor findings (e.g., missing signature).
    assert response.report.verdict.value in ("ALLOW", "WARN")


async def test_orchestrator_with_dynamic_enabled(clean_bundle: Path) -> None:
    orchestrator = Orchestrator()
    response = await orchestrator.scan(
        ScanRequest(bundle_path=clean_bundle, enable_dynamic=True)
    )
    assert response.report is not None


def test_orchestrator_raises_on_missing_path(tmp_path: Path) -> None:
    orchestrator = Orchestrator()
    with pytest.raises(FileNotFoundError):
        asyncio.run(
            orchestrator.scan(ScanRequest(bundle_path=tmp_path / "nope", enable_dynamic=False))
        )

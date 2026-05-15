"""Smoke tests for the CLI surface."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from skillsentinel.cli.main import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "SkillSentinel" in result.stdout


def test_cli_scan_smoke(tmp_path: Path) -> None:
    """Smoke test: CLI runs end-to-end on a complete (if minimal) bundle."""
    bundle = tmp_path / "skill"
    bundle.mkdir()
    (bundle / "skill.yaml").write_text(
        "name: smoke\n"
        "version: 0.0.1\n"
        "description: Minimal smoke-test bundle.\n"
        "entrypoint: run.py\n",
        encoding="utf-8",
    )
    (bundle / "run.py").write_text("print('hi')\n", encoding="utf-8")
    result = runner.invoke(app, ["scan", str(bundle), "--no-dynamic"])
    assert result.exit_code == 0
    # Any of the four verdicts is a valid pipeline run; we only assert the CLI
    # didn't crash and emitted one of them.
    assert any(v in result.stdout for v in ("ALLOW", "WARN", "REVIEW", "BLOCK"))


def test_cli_doctor_not_yet_implemented() -> None:
    result = runner.invoke(app, ["doctor"])
    # Phase-0 stubs exit 2 with a friendly message.
    assert result.exit_code == 2

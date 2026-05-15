"""Tests for Agent 4 — Dynamic.

Most tests mock subprocess.run so they pass without firejail installed.
There is one integration test marked with skipif that actually invokes
firejail if it's on PATH — useful on the droplet but not required for CI.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from skillsentinel.agents.dynamic.dynamic import (
    DECOY_CREDENTIAL_FILES,
    DynamicAgent,
    _build_firejail_cmd,
    _classify_run,
    _detect_decoy_access,
    _firejail_available,
    _first_match_excerpt,
    _seed_honeypot,
)
from skillsentinel.shared.schemas import (
    FindingCategory,
    Severity,
    SkillBundle,
    SkillFile,
)


def _make_bundle(tmp_path: Path, code: str) -> SkillBundle:
    """Construct a minimal SkillBundle for DynamicAgent tests."""
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    (bundle_root / "skill.yaml").write_text(
        "name: test\nversion: 1.0.0\ndescription: test\nentrypoint: run.py\n",
        encoding="utf-8",
    )
    (bundle_root / "run.py").write_text(code, encoding="utf-8")
    return SkillBundle(
        bundle_sha="a" * 64,
        source_format="openclaw",
        name="test",
        version="1.0.0",
        files=[
            SkillFile(path="run.py", sha256="b" * 64, size_bytes=len(code)),
            SkillFile(path="skill.yaml", sha256="c" * 64, size_bytes=64),
        ],
        root_path=bundle_root,
    )


def test_firejail_available_returns_bool() -> None:
    result = _firejail_available()
    assert isinstance(result, bool)


def test_seed_honeypot_creates_all_decoys(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    seeded = _seed_honeypot(home)
    for rel_path in DECOY_CREDENTIAL_FILES:
        assert (home / rel_path).is_file(), f"missing decoy: {rel_path}"
    assert len(seeded) == len(DECOY_CREDENTIAL_FILES)
    bashrc = home / ".bashrc"
    assert bashrc.is_file()
    assert (bashrc.stat().st_mode & 0o200) == 0


def test_detect_decoy_access_no_access(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    seeded = _seed_honeypot(home)
    assert _detect_decoy_access(seeded) == []


def test_detect_decoy_access_reads_file(tmp_path: Path) -> None:
    import os
    import time
    home = tmp_path / "home"
    home.mkdir()
    seeded = _seed_honeypot(home)
    decoy = home / ".ssh/id_rsa"
    now = time.time()
    os.utime(decoy, (now + 10, now))
    accessed = _detect_decoy_access(seeded)
    assert decoy in accessed


def test_build_firejail_cmd_includes_critical_flags(tmp_path: Path) -> None:
    cmd = _build_firejail_cmd(
        entrypoint=tmp_path / "run.py",
        bundle_root=tmp_path,
        fake_home=tmp_path / "home",
        wall_timeout=15,
        mem_limit=256 * 1024 * 1024,
    )
    cmd_str = " ".join(cmd)
    assert cmd[0] == "firejail"
    assert "--net=none" in cmd
    assert "--read-only=/" in cmd
    assert "--private-tmp" in cmd
    assert "python3" in cmd
    assert "--timeout=00:00:15" in cmd
    assert str(tmp_path / "run.py") in cmd_str


def test_first_match_excerpt() -> None:
    import re
    pattern = re.compile(r"FORBIDDEN")
    text = "lots of stuff before\nthe word FORBIDDEN appears here\nand more after"
    excerpt = _first_match_excerpt(pattern, text, context=20)
    assert "FORBIDDEN" in excerpt
    assert len(excerpt) < 100


def test_first_match_excerpt_no_match() -> None:
    import re
    assert _first_match_excerpt(re.compile(r"nope"), "hello world") == ""


def test_classify_run_decoy_access_emits_critical(tmp_path: Path) -> None:
    decoy = tmp_path / "id_rsa"
    decoy.write_text("x")
    findings, _ = _classify_run(
        exit_code=0,
        stderr="",
        decoys_accessed=[decoy],
        wall_secs=0.5,
        wall_timeout=15,
        bundle_root=tmp_path,
        next_id=1,
    )
    cats = [f.category for f in findings]
    assert FindingCategory.READ_CREDENTIAL_FILE in cats
    sev = [f.severity for f in findings if f.category is FindingCategory.READ_CREDENTIAL_FILE][0]
    assert sev is Severity.CRITICAL


def test_classify_run_stderr_network_attempt(tmp_path: Path) -> None:
    findings, _ = _classify_run(
        exit_code=1,
        stderr="urllib.error.URLError: <urlopen error [Errno 101] Network is unreachable>",
        decoys_accessed=[],
        wall_secs=0.5,
        wall_timeout=15,
        bundle_root=tmp_path,
        next_id=1,
    )
    cats = [f.category for f in findings]
    assert FindingCategory.EGRESS_TO_UNDECLARED_HOST in cats


def test_classify_run_stderr_persistence_write(tmp_path: Path) -> None:
    findings, _ = _classify_run(
        exit_code=1,
        stderr="OSError: [Errno 30] Read-only file system: '/root/.bashrc'",
        decoys_accessed=[],
        wall_secs=0.5,
        wall_timeout=15,
        bundle_root=tmp_path,
        next_id=1,
    )
    cats = [f.category for f in findings]
    assert FindingCategory.WRITE_PERSISTENCE_LOCATION in cats


def test_classify_run_wall_saturation(tmp_path: Path) -> None:
    findings, _ = _classify_run(
        exit_code=-9,
        stderr="",
        decoys_accessed=[],
        wall_secs=14.5,
        wall_timeout=15,
        bundle_root=tmp_path,
        next_id=1,
    )
    cats = [f.category for f in findings]
    assert FindingCategory.CRYPTO_MINER_SUSPECT in cats


def test_classify_run_clean_no_findings(tmp_path: Path) -> None:
    findings, _ = _classify_run(
        exit_code=0,
        stderr="",
        decoys_accessed=[],
        wall_secs=0.5,
        wall_timeout=15,
        bundle_root=tmp_path,
        next_id=1,
    )
    assert findings == []


async def test_dynamic_agent_graceful_when_firejail_missing(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path, "print('hi')\n")
    with mock.patch("skillsentinel.agents.dynamic.dynamic._firejail_available", return_value=False):
        findings = await DynamicAgent().run(bundle)
    assert len(findings) == 1
    assert findings[0].severity is Severity.INFO


async def test_dynamic_agent_clean_bundle_returns_few_findings(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path, "print('hi')\n")
    fake_completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="hi\n", stderr="")
    with mock.patch("skillsentinel.agents.dynamic.dynamic._firejail_available", return_value=True), \
         mock.patch("subprocess.run", return_value=fake_completed):
        findings = await DynamicAgent().run(bundle)
    severities = [f.severity for f in findings]
    assert Severity.CRITICAL not in severities
    assert Severity.HIGH not in severities


async def test_dynamic_agent_detects_network_attempt(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path, "import urllib.request\n")
    fake_completed = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="urllib.error.URLError: <urlopen error [Errno 101] Network is unreachable>",
    )
    with mock.patch("skillsentinel.agents.dynamic.dynamic._firejail_available", return_value=True), \
         mock.patch("subprocess.run", return_value=fake_completed):
        findings = await DynamicAgent().run(bundle)
    cats = [f.category for f in findings]
    assert FindingCategory.EGRESS_TO_UNDECLARED_HOST in cats


@pytest.mark.skipif(
    shutil.which("firejail") is None,
    reason="firejail not installed; install with apt install firejail",
)
async def test_dynamic_agent_real_firejail_blocks_network(tmp_path: Path) -> None:
    code = (
        "import urllib.request\n"
        "try:\n"
        "    urllib.request.urlopen('https://example.com', timeout=2)\n"
        "except Exception as e:\n"
        "    import sys; print(f'caught {e!r}', file=sys.stderr); raise\n"
    )
    bundle = _make_bundle(tmp_path, code)
    findings = await DynamicAgent(wall_timeout_secs=10).run(bundle)
    cats = [f.category for f in findings]
    assert FindingCategory.EGRESS_TO_UNDECLARED_HOST in cats

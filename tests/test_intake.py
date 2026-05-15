"""Tests for Agent 1 — Intake.

Each test builds a small bundle on tmp_path and asserts which findings the
agent should emit. Keep tests focused: one structural defect per test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillsentinel.agents.intake import IntakeAgent
from skillsentinel.shared.schemas import FindingCategory, Severity


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _make_bundle(root: Path, manifest: str, files: dict[str, str] | None = None) -> Path:
    """Create a bundle directory at ``root`` with the given manifest + files."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "skill.yaml").write_text(manifest, encoding="utf-8")
    for path, content in (files or {}).items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return root


CLEAN_MANIFEST = (
    "name: hello-skill\n"
    "version: 1.0.0\n"
    "description: A friendly hello-world skill.\n"
    "entrypoint: run.py\n"
)


# ----------------------------------------------------------------------------
# Sanity: clean bundle → only SIGNATURE_MISSING
# ----------------------------------------------------------------------------
async def test_clean_bundle_yields_only_signature_missing(tmp_path: Path) -> None:
    bundle_path = _make_bundle(
        tmp_path / "clean",
        CLEAN_MANIFEST,
        {"run.py": "print('hello')\n"},
    )
    bundle = await IntakeAgent().run(bundle_path)

    assert bundle.source_format == "openclaw"
    assert bundle.name == "hello-skill"
    assert bundle.version == "1.0.0"
    assert len(bundle.files) == 2  # skill.yaml + run.py
    assert len(bundle.bundle_sha) == 64

    categories = [f.category for f in bundle.findings]
    assert categories == [FindingCategory.SIGNATURE_MISSING]
    assert bundle.findings[0].severity is Severity.LOW


# ----------------------------------------------------------------------------
# MANIFEST_INVALID — missing required fields
# ----------------------------------------------------------------------------
async def test_missing_name_field_flagged(tmp_path: Path) -> None:
    bundle = await IntakeAgent().run(
        _make_bundle(
            tmp_path / "no-name",
            "version: 1.0.0\ndescription: x\nentrypoint: run.py\n",
            {"run.py": "pass\n"},
        )
    )
    invalid = [f for f in bundle.findings if f.category is FindingCategory.MANIFEST_INVALID]
    assert any("'name'" in f.message for f in invalid)


async def test_entrypoint_must_exist_in_bundle(tmp_path: Path) -> None:
    bundle = await IntakeAgent().run(
        _make_bundle(
            tmp_path / "phantom-entry",
            CLEAN_MANIFEST.replace("entrypoint: run.py", "entrypoint: ghost.py"),
            {"run.py": "pass\n"},
        )
    )
    invalid = [f for f in bundle.findings if f.category is FindingCategory.MANIFEST_INVALID]
    assert any("ghost.py" in f.message for f in invalid)


async def test_malformed_yaml_is_critical(tmp_path: Path) -> None:
    # Tabs + colons in unquoted YAML strings explode the parser.
    broken = "name: x\nversion: 1.0\n  ::: not yaml :::\n"
    bundle_path = tmp_path / "broken"
    bundle_path.mkdir()
    (bundle_path / "skill.yaml").write_text(broken, encoding="utf-8")
    (bundle_path / "run.py").write_text("pass\n", encoding="utf-8")

    bundle = await IntakeAgent().run(bundle_path)
    crit = [f for f in bundle.findings if f.severity is Severity.CRITICAL]
    assert len(crit) >= 1
    assert crit[0].category is FindingCategory.MANIFEST_INVALID


# ----------------------------------------------------------------------------
# MANIFEST_OVER_BROAD — too many capabilities
# ----------------------------------------------------------------------------
async def test_over_broad_capabilities_flagged(tmp_path: Path) -> None:
    caps_yaml = "\n".join(f"  - cap:{i}" for i in range(15))
    manifest = CLEAN_MANIFEST + "capabilities:\n" + caps_yaml + "\n"
    bundle = await IntakeAgent().run(
        _make_bundle(tmp_path / "broad", manifest, {"run.py": "pass\n"})
    )
    broad = [f for f in bundle.findings if f.category is FindingCategory.MANIFEST_OVER_BROAD]
    assert len(broad) == 1
    assert broad[0].severity is Severity.MEDIUM


async def test_few_capabilities_not_flagged(tmp_path: Path) -> None:
    manifest = CLEAN_MANIFEST + "capabilities:\n  - fs:read\n  - network:outbound\n"
    bundle = await IntakeAgent().run(
        _make_bundle(tmp_path / "fine", manifest, {"run.py": "pass\n"})
    )
    broad = [f for f in bundle.findings if f.category is FindingCategory.MANIFEST_OVER_BROAD]
    assert broad == []


# ----------------------------------------------------------------------------
# SIGNATURE_MISSING — present when no signature exists
# ----------------------------------------------------------------------------
async def test_signature_in_manifest_suppresses_finding(tmp_path: Path) -> None:
    manifest = CLEAN_MANIFEST + "signature: ed25519:aabbccdd...\n"
    bundle = await IntakeAgent().run(
        _make_bundle(tmp_path / "signed", manifest, {"run.py": "pass\n"})
    )
    sig_findings = [f for f in bundle.findings if f.category is FindingCategory.SIGNATURE_MISSING]
    assert sig_findings == []


async def test_signature_file_suppresses_finding(tmp_path: Path) -> None:
    bundle = await IntakeAgent().run(
        _make_bundle(
            tmp_path / "signed-file",
            CLEAN_MANIFEST,
            {"run.py": "pass\n", "skill.sig": "deadbeef\n"},
        )
    )
    sig_findings = [f for f in bundle.findings if f.category is FindingCategory.SIGNATURE_MISSING]
    assert sig_findings == []


# ----------------------------------------------------------------------------
# DEPENDENCY_UNDECLARED — code imports something not in manifest
# ----------------------------------------------------------------------------
async def test_undeclared_third_party_import_flagged(tmp_path: Path) -> None:
    bundle = await IntakeAgent().run(
        _make_bundle(
            tmp_path / "undeclared",
            CLEAN_MANIFEST,
            {"run.py": "import requests\nrequests.get('https://example.com')\n"},
        )
    )
    undeclared = [f for f in bundle.findings
                  if f.category is FindingCategory.DEPENDENCY_UNDECLARED]
    assert len(undeclared) == 1
    assert undeclared[0].extra["module"] == "requests"
    assert undeclared[0].evidence is not None
    assert undeclared[0].evidence.file_path == "run.py"


async def test_declared_dependency_not_flagged(tmp_path: Path) -> None:
    manifest = CLEAN_MANIFEST + "dependencies:\n  - requests>=2.0\n"
    bundle = await IntakeAgent().run(
        _make_bundle(
            tmp_path / "declared",
            manifest,
            {"run.py": "import requests\n"},
        )
    )
    undeclared = [f for f in bundle.findings
                  if f.category is FindingCategory.DEPENDENCY_UNDECLARED]
    assert undeclared == []


async def test_stdlib_imports_not_flagged(tmp_path: Path) -> None:
    bundle = await IntakeAgent().run(
        _make_bundle(
            tmp_path / "stdlib-only",
            CLEAN_MANIFEST,
            {"run.py": "import os\nimport sys\nimport json\nimport hashlib\n"},
        )
    )
    undeclared = [f for f in bundle.findings
                  if f.category is FindingCategory.DEPENDENCY_UNDECLARED]
    assert undeclared == []


# ----------------------------------------------------------------------------
# Error handling
# ----------------------------------------------------------------------------
async def test_missing_bundle_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        await IntakeAgent().run(tmp_path / "does-not-exist")


async def test_file_instead_of_dir_raises(tmp_path: Path) -> None:
    p = tmp_path / "i-am-a-file.txt"
    p.write_text("hi", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        await IntakeAgent().run(p)


# ----------------------------------------------------------------------------
# Bundle SHA determinism
# ----------------------------------------------------------------------------
async def test_bundle_sha_is_deterministic(tmp_path: Path) -> None:
    """Same contents → same sha, regardless of file creation order."""
    a = _make_bundle(tmp_path / "a", CLEAN_MANIFEST, {"run.py": "print('x')\n"})
    b = _make_bundle(tmp_path / "b", CLEAN_MANIFEST, {"run.py": "print('x')\n"})

    sha_a = (await IntakeAgent().run(a)).bundle_sha
    sha_b = (await IntakeAgent().run(b)).bundle_sha
    assert sha_a == sha_b


async def test_changed_content_changes_sha(tmp_path: Path) -> None:
    a = _make_bundle(tmp_path / "a", CLEAN_MANIFEST, {"run.py": "print('x')\n"})
    b = _make_bundle(tmp_path / "b", CLEAN_MANIFEST, {"run.py": "print('DIFFERENT')\n"})

    sha_a = (await IntakeAgent().run(a)).bundle_sha
    sha_b = (await IntakeAgent().run(b)).bundle_sha
    assert sha_a != sha_b


# ----------------------------------------------------------------------------
# Corpus smoke test — run against all 10 hand-crafted bundles
# ----------------------------------------------------------------------------
CORPUS_ROOT = Path(__file__).resolve().parent.parent / "corpus"


@pytest.mark.parametrize(
    "label,path",
    [
        ("malicious-01", "malicious/01-credential-exfiltrator"),
        ("malicious-02", "malicious/02-prompt-injection"),
        ("malicious-03", "malicious/03-typosquat-dependency"),
        ("malicious-04", "malicious/04-time-bomb"),
        ("malicious-05", "malicious/05-living-off-the-land"),
        ("benign-01",    "benign/01-currency-converter"),
        ("benign-02",    "benign/02-aws-deployer"),
        ("benign-03",    "benign/03-pdf-extractor"),
        ("benign-04",    "benign/04-code-formatter"),
        ("benign-05",    "benign/05-news-summarizer"),
    ],
)
async def test_corpus_bundle_intake_runs_without_error(label: str, path: str) -> None:
    """Every corpus bundle should parse — no exceptions, well-formed output."""
    bundle = await IntakeAgent().run(CORPUS_ROOT / path)
    assert bundle.name
    assert bundle.version
    assert bundle.bundle_sha
    assert len(bundle.bundle_sha) == 64
    assert bundle.source_format in ("openclaw", "claude_code", "openai_plugin", "unknown")


async def test_typosquat_corpus_caught_by_dependency_check() -> None:
    """Malicious 03 typosquats Pillow as 'pillow_image' — Intake's dep check should catch it."""
    bundle = await IntakeAgent().run(CORPUS_ROOT / "malicious/03-typosquat-dependency")
    undeclared = [f for f in bundle.findings
                  if f.category is FindingCategory.DEPENDENCY_UNDECLARED]
    assert len(undeclared) >= 1
    assert "pillow_image" in undeclared[0].message

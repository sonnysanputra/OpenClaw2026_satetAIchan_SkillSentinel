"""Agent 1 — Intake (structural analyzer).

The cheapest, fastest, most deterministic agent in the pipeline. It answers
one question:

    "Is this skill bundle structurally well-formed,
     and did the publisher declare what it claims to be?"

Intake is **not** a malware detector. It can't tell whether the code actually
does what the manifest says — that's Agent 3 (Semantic). It can only check
whether the publisher even *tried* to describe their skill honestly.

Why have Intake at all if it can't catch lies?

* **Fast first pass.** A bundle that's structurally broken can be rejected
  in milliseconds, before we burn LLM tokens or sandbox runs on it.
* **Forces honest publishers.** Legit authors fill out manifests. Adversaries
  often don't bother — typos, missing fields, contradictions. Intake findings
  are cheap signal even when individually low-severity.
* **Canonical bundle representation.** Intake produces the ``SkillBundle``
  object every other agent consumes. Without Intake, no agent has a stable
  view of the bundle.

The four kinds of findings Intake can emit (and only these):

    MANIFEST_INVALID          — required fields missing / malformed
    MANIFEST_OVER_BROAD       — claims an unusually large capability set
    SIGNATURE_MISSING         — no signature field or .sig file
    DEPENDENCY_UNDECLARED     — code imports module not in declared deps

Everything else is somebody else's problem, by design.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from skillsentinel.shared.schemas import (
    EvidencePointer,
    Finding,
    FindingCategory,
    Severity,
    SkillBundle,
    SkillFile,
)

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

# Fields every OpenClaw skill manifest must define. Missing any of these is a
# HIGH-severity MANIFEST_INVALID finding — the bundle can't be safely installed
# because we don't even know what to call it or how to run it.
REQUIRED_MANIFEST_FIELDS: tuple[str, ...] = ("name", "version", "description", "entrypoint")

# Threshold for MANIFEST_OVER_BROAD. Legitimate skills typically claim 1–4
# capabilities. Anything past this hints that the publisher is either pasting
# a kitchen-sink template or trying to grant themselves more access than they
# need ("ambient authority creep").
OVER_BROAD_CAPABILITY_COUNT = 10

# Files anywhere in the bundle that count as a signature. Presence (even
# unverified) bumps trust slightly; absence is a LOW finding rather than HIGH,
# because most ClawHub skills today are unsigned.
SIGNATURE_FILE_PATTERNS: tuple[str, ...] = (
    "signature",
    "signature.txt",
    "signature.asc",
    "skill.sig",
    ".sig",
)

# Standard-library module names we should NOT flag as undeclared dependencies.
# The list is intentionally conservative — Python's stdlib is huge but agents
# typically use a small slice of it. We keep this short and curate it rather
# than vendor the whole stdlib list, because false positives here hurt more
# than false negatives (Agent 2's static analyzer catches anything weird).
STDLIB_MODULES: frozenset[str] = frozenset({
    "os", "sys", "io", "re", "json", "yaml", "time", "datetime",
    "pathlib", "subprocess", "shutil", "tempfile", "hashlib", "base64",
    "urllib", "http", "socket", "ssl", "logging", "argparse", "typing",
    "collections", "itertools", "functools", "math", "random", "string",
    "platform", "getpass", "warnings", "traceback", "asyncio", "threading",
    "multiprocessing", "concurrent", "queue", "select", "signal", "atexit",
    "ast", "inspect", "importlib", "pkgutil", "abc", "contextlib", "copy",
    "enum", "dataclasses",
})

# Regex for Python `import X` / `from X import ...` lines. Catches both at
# top of file. Multi-line imports and conditional imports are out of scope —
# Agent 2 does proper AST-level analysis if we want exhaustive coverage.
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([A-Za-z_][A-Za-z0-9_]*)|import\s+([A-Za-z_][A-Za-z0-9_]*))",
    re.MULTILINE,
)


# ----------------------------------------------------------------------------
# Bundle walking — pure file I/O, no judgment
# ----------------------------------------------------------------------------
def _walk_bundle(root: Path) -> tuple[list[SkillFile], str]:
    """Walk ``root`` recursively, hashing every file.

    Returns:
        (files, bundle_sha) — bundle_sha is the SHA-256 of the sorted,
        newline-joined list of "<sha256>  <relative-path>" lines. This makes
        the bundle hash deterministic regardless of file order.
    """
    files: list[SkillFile] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        # Skip caches and editor cruft — they're irrelevant and pollute hashes.
        rel = path.relative_to(root).as_posix()
        if "__pycache__" in rel or rel.endswith(".pyc") or rel.startswith(".git/"):
            continue
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        files.append(SkillFile(path=rel, sha256=sha, size_bytes=len(data)))

    # Deterministic bundle hash. Sorting by path means file system traversal
    # order can't influence the hash, which is critical for cache lookups.
    manifest_lines = "\n".join(f"{f.sha256}  {f.path}" for f in files)
    bundle_sha = hashlib.sha256(manifest_lines.encode("utf-8")).hexdigest()
    return files, bundle_sha


# ----------------------------------------------------------------------------
# Format detection
# ----------------------------------------------------------------------------
def _detect_format(root: Path) -> str:
    """Identify which skill ecosystem this bundle belongs to."""
    if (root / "skill.yaml").is_file() or (root / "skill.yml").is_file():
        return "openclaw"
    if (root / "skill.json").is_file():
        return "claude_code"
    if (root / ".well-known" / "ai-plugin.json").is_file():
        return "openai_plugin"
    return "unknown"


# ----------------------------------------------------------------------------
# Manifest parsing — OpenClaw YAML only for now
# ----------------------------------------------------------------------------
def _parse_openclaw_manifest(root: Path) -> tuple[dict[str, Any], Path | None, str | None]:
    """Load the bundle's ``skill.yaml`` (or ``skill.yml``).

    Returns:
        (manifest_dict, manifest_path, parse_error)
        - manifest_dict is {} if no manifest exists or parsing failed.
        - parse_error is None on success, else a human-readable string.
    """
    candidates = [root / "skill.yaml", root / "skill.yml"]
    manifest_path = next((p for p in candidates if p.is_file()), None)
    if manifest_path is None:
        return {}, None, "no manifest found (expected skill.yaml)"

    try:
        raw = manifest_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return {}, manifest_path, f"YAML parse error: {exc}"
    except OSError as exc:
        return {}, manifest_path, f"read error: {exc}"

    if not isinstance(parsed, dict):
        return {}, manifest_path, f"manifest top-level is {type(parsed).__name__}, expected mapping"

    return parsed, manifest_path, None


# ----------------------------------------------------------------------------
# Check #1 — Required fields exist and are well-typed
# ----------------------------------------------------------------------------
def _check_required_fields(
    manifest: dict[str, Any],
    manifest_path: Path | None,
    parse_error: str | None,
    bundle_files: list[SkillFile],
    next_id: int,
) -> tuple[list[Finding], int]:
    """Emit MANIFEST_INVALID findings for missing/malformed required fields."""
    findings: list[Finding] = []

    # If the manifest didn't parse at all, that's a single CRITICAL finding.
    # The orchestrator will see this and short-circuit (no point running other
    # agents on a bundle we can't even read the manifest of).
    if parse_error is not None:
        findings.append(Finding(
            id=f"F-{next_id:04d}",
            agent="intake",
            category=FindingCategory.MANIFEST_INVALID,
            severity=Severity.CRITICAL,
            confidence=1.0,
            message=f"Manifest unparseable: {parse_error}",
            evidence=EvidencePointer(
                file_path=str(manifest_path.relative_to(manifest_path.parent.parent))
                if manifest_path else None,
            ),
        ))
        return findings, next_id + 1

    # Required-field presence check.
    for field in REQUIRED_MANIFEST_FIELDS:
        value = manifest.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            findings.append(Finding(
                id=f"F-{next_id:04d}",
                agent="intake",
                category=FindingCategory.MANIFEST_INVALID,
                severity=Severity.HIGH,
                confidence=1.0,
                message=f"Missing required manifest field: {field!r}",
            ))
            next_id += 1

    # Entrypoint must point at a real file in the bundle.
    entrypoint = manifest.get("entrypoint")
    if isinstance(entrypoint, str) and entrypoint.strip():
        file_paths = {f.path for f in bundle_files}
        if entrypoint not in file_paths:
            findings.append(Finding(
                id=f"F-{next_id:04d}",
                agent="intake",
                category=FindingCategory.MANIFEST_INVALID,
                severity=Severity.HIGH,
                confidence=1.0,
                message=f"Entrypoint {entrypoint!r} not found in bundle",
                extra={"declared_entrypoint": entrypoint},
            ))
            next_id += 1

    return findings, next_id


# ----------------------------------------------------------------------------
# Check #2 — Capability set is not absurdly broad
# ----------------------------------------------------------------------------
def _check_capability_breadth(
    manifest: dict[str, Any],
    next_id: int,
) -> tuple[list[Finding], int]:
    """Emit MANIFEST_OVER_BROAD if the skill claims too many capabilities."""
    caps = manifest.get("capabilities") or []
    if not isinstance(caps, list):
        return [], next_id

    if len(caps) > OVER_BROAD_CAPABILITY_COUNT:
        finding = Finding(
            id=f"F-{next_id:04d}",
            agent="intake",
            category=FindingCategory.MANIFEST_OVER_BROAD,
            severity=Severity.MEDIUM,
            confidence=0.7,  # Heuristic — could be a legitimate kitchen-sink tool.
            message=(
                f"Skill declares {len(caps)} capabilities "
                f"(threshold {OVER_BROAD_CAPABILITY_COUNT}). "
                "Verify each is actually needed."
            ),
            extra={"capability_count": str(len(caps))},
        )
        return [finding], next_id + 1
    return [], next_id


# ----------------------------------------------------------------------------
# Check #3 — Signature presence (LOW finding when missing)
# ----------------------------------------------------------------------------
def _check_signature(
    manifest: dict[str, Any],
    bundle_files: list[SkillFile],
    next_id: int,
) -> tuple[list[Finding], int]:
    """Emit SIGNATURE_MISSING if neither manifest nor bundle has a signature."""
    # Manifest may declare an inline signature field.
    if manifest.get("signature"):
        return [], next_id

    # Or there may be a .sig / signature file in the bundle.
    file_paths_lower = {f.path.lower() for f in bundle_files}
    for pattern in SIGNATURE_FILE_PATTERNS:
        if any(p.endswith(pattern) for p in file_paths_lower):
            return [], next_id

    finding = Finding(
        id=f"F-{next_id:04d}",
        agent="intake",
        category=FindingCategory.SIGNATURE_MISSING,
        severity=Severity.LOW,
        confidence=1.0,
        message="No publisher signature found. Origin cannot be cryptographically verified.",
    )
    return [finding], next_id + 1


# ----------------------------------------------------------------------------
# Check #4 — Code imports match declared dependencies
# ----------------------------------------------------------------------------
def _check_dependency_coherence(
    root: Path,
    manifest: dict[str, Any],
    bundle_files: list[SkillFile],
    next_id: int,
) -> tuple[list[Finding], int]:
    """Emit DEPENDENCY_UNDECLARED for imported modules not in declared deps.

    We only scan .py files for now. Future iterations can add JS/TS via a
    different regex or proper AST parsing.
    """
    declared = {str(d).split("==")[0].split(">=")[0].split("<")[0].strip().lower()
                for d in (manifest.get("dependencies") or [])}

    # Build set of imported top-level modules across all .py files in the bundle.
    imported: dict[str, list[tuple[str, int]]] = {}  # module -> [(file, line)]
    for f in bundle_files:
        if not f.path.endswith(".py"):
            continue
        try:
            text = (root / f.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in _IMPORT_RE.finditer(text):
            module = (match.group(1) or match.group(2)).split(".")[0].lower()
            if module in STDLIB_MODULES:
                continue
            line_no = text[: match.start()].count("\n") + 1
            imported.setdefault(module, []).append((f.path, line_no))

    findings: list[Finding] = []
    for module, occurrences in sorted(imported.items()):
        if module in declared:
            continue
        # Pick the first occurrence for evidence.
        file_path, line_no = occurrences[0]
        findings.append(Finding(
            id=f"F-{next_id:04d}",
            agent="intake",
            category=FindingCategory.DEPENDENCY_UNDECLARED,
            severity=Severity.MEDIUM,
            confidence=0.85,
            message=(
                f"Code imports {module!r} but it is not in manifest 'dependencies'. "
                "Publisher may be hiding a dependency or relying on host-installed packages."
            ),
            evidence=EvidencePointer(file_path=file_path, line_start=line_no),
            extra={"module": module, "occurrences": str(len(occurrences))},
        ))
        next_id += 1
    return findings, next_id


# ----------------------------------------------------------------------------
# Public agent class
# ----------------------------------------------------------------------------
class IntakeAgent:
    """Parse + validate a skill bundle on disk. Returns a SkillBundle.

    Called by the orchestrator as ``await intake.run(bundle_path)``.
    """

    async def run(self, bundle_path: Path) -> SkillBundle:
        if not bundle_path.exists():
            msg = f"Bundle path does not exist: {bundle_path}"
            raise FileNotFoundError(msg)
        if not bundle_path.is_dir():
            msg = f"Bundle path is not a directory: {bundle_path}"
            raise NotADirectoryError(msg)

        # Phase A — Walk the bundle and compute hashes.
        files, bundle_sha = _walk_bundle(bundle_path)

        # Phase B — Detect format. Today we only fully parse OpenClaw; other
        # formats fall through with an unknown source_format and minimal manifest.
        fmt = _detect_format(bundle_path)
        if fmt == "openclaw":
            manifest, manifest_path, parse_err = _parse_openclaw_manifest(bundle_path)
        else:
            # Best-effort: try OpenClaw parser anyway, in case skill.yaml exists
            # but isn't at the root for some reason.
            manifest, manifest_path, parse_err = _parse_openclaw_manifest(bundle_path)

        # Phase C — Run all four checks. Each helper returns (findings, next_id)
        # so finding IDs stay globally unique within the scan.
        next_id = 1
        all_findings: list[Finding] = []

        f1, next_id = _check_required_fields(manifest, manifest_path, parse_err, files, next_id)
        all_findings.extend(f1)

        f2, next_id = _check_capability_breadth(manifest, next_id)
        all_findings.extend(f2)

        f3, next_id = _check_signature(manifest, files, next_id)
        all_findings.extend(f3)

        # Skip dep coherence if the manifest didn't parse — we can't check
        # against deps we don't know about.
        if parse_err is None and manifest:
            f4, _ = _check_dependency_coherence(bundle_path, manifest, files, next_id)
            all_findings.extend(f4)

        # Phase D — Assemble the canonical bundle representation.
        bundle = SkillBundle(
            bundle_sha=bundle_sha,
            source_format=fmt,  # type: ignore[arg-type]
            name=str(manifest.get("name") or bundle_path.name),
            version=str(manifest.get("version") or "0.0.0"),
            publisher=manifest.get("publisher"),
            declared_description=manifest.get("description"),
            declared_capabilities=list(manifest.get("capabilities") or []),
            declared_dependencies=list(manifest.get("dependencies") or []),
            files=files,
            root_path=bundle_path,
            findings=all_findings,
        )
        log.info(
            "intake.parsed",
            extra={
                "path": str(bundle_path),
                "bundle_sha": bundle_sha,
                "format": fmt,
                "n_files": len(files),
                "n_findings": len(all_findings),
            },
        )
        return bundle

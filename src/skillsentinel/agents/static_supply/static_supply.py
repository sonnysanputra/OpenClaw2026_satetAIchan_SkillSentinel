"""Agent 2 — Static & Supply-Chain analyzer.

**Modality:** AST + regex code analysis.
**Question answered:** "Are there dangerous patterns or hidden payloads in the source?"

Checks:
  - Dangerous calls: eval(), exec(), os.system(), subprocess(..., shell=True)
  - Obfuscated execution: base64.b64decode(...) followed by exec()
  - Hardcoded secrets: regex for API keys, tokens, AWS keys
  - Typosquat-likely packages: Levenshtein distance from popular package names

Findings emitted:
    CODE_DANGEROUS_PATTERN  -- direct dangerous call (HIGH)
    CODE_OBFUSCATED         -- base64 decode + exec pattern (HIGH)
    SECRET_LEAKED           -- API key / token regex match (MEDIUM)
    TYPOSQUAT_LIKELY        -- import close to popular package (MEDIUM)
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from skillsentinel.shared.schemas import (
    EvidencePointer,
    Finding,
    FindingCategory,
    Severity,
)

if TYPE_CHECKING:
    from skillsentinel.shared import SkillBundle

log = logging.getLogger(__name__)

# Calls treated as dangerous when invoked. Each is a (module, function) pair.
DANGEROUS_CALLS: tuple[tuple[str | None, str], ...] = (
    (None,      "eval"),
    (None,      "exec"),
    (None,      "compile"),
    (None,      "__import__"),
    ("os",      "system"),
    ("os",      "popen"),
    ("os",      "execv"),
    ("os",      "execvp"),
    ("subprocess", "call"),
    ("subprocess", "Popen"),
    ("subprocess", "run"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("pickle",  "loads"),
    ("marshal", "loads"),
)

# Regex patterns for likely hardcoded secrets.
SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'AKIA[0-9A-Z]{16}'),                "AWS access key"),
    (re.compile(r'AIza[0-9A-Za-z_-]{35}'),           "Google API key"),
    (re.compile(r'ghp_[A-Za-z0-9]{36,}'),            "GitHub personal access token"),
    (re.compile(r'github_pat_[A-Za-z0-9_]{82,}'),    "GitHub fine-grained PAT"),
    (re.compile(r'sk-[A-Za-z0-9]{20,}'),             "OpenAI/Anthropic-style API key"),
    (re.compile(r'xox[baprs]-[A-Za-z0-9-]{10,}'),    "Slack token"),
)

# Popular packages a typosquat might mimic. Distance-2 or fewer = suspicious.
POPULAR_PACKAGES: frozenset[str] = frozenset({
    "requests", "numpy", "pandas", "django", "flask", "fastapi",
    "sqlalchemy", "pillow", "tensorflow", "torch", "scikit-learn",
    "matplotlib", "pytest", "click", "yaml", "boto3", "urllib3",
    "cryptography", "anthropic", "openai", "discord", "discord.py",
})


def _levenshtein(a: str, b: str) -> int:
    """Standard Levenshtein edit distance."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur_row = [i]
        for j, cb in enumerate(b, start=1):
            cur_row.append(min(
                prev_row[j] + 1,        # deletion
                cur_row[j - 1] + 1,     # insertion
                prev_row[j - 1] + (ca != cb),  # substitution
            ))
        prev_row = cur_row
    return prev_row[-1]


def _qualified_name(node: ast.AST) -> tuple[str | None, str]:
    """Return (module_or_None, name) for a Call's func node.
    e.g. os.system(...) -> ("os", "system"), eval(...) -> (None, "eval")."""
    if isinstance(node, ast.Name):
        return None, node.id
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name):
            return node.value.id, node.attr
    return None, ""


def _check_dangerous_ast(tree: ast.AST, file_path: str, next_id: int) -> tuple[list[Finding], int]:
    """Walk AST; flag CODE_DANGEROUS_PATTERN findings."""
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        mod, name = _qualified_name(node.func)
        for danger_mod, danger_name in DANGEROUS_CALLS:
            if name == danger_name and (danger_mod is None or mod == danger_mod):
                # subprocess with shell=True is the dangerous form; without, it's fine
                if danger_mod == "subprocess":
                    shell_true = any(
                        isinstance(kw, ast.keyword)
                        and kw.arg == "shell"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                        for kw in node.keywords
                    )
                    if not shell_true:
                        continue
                qual = f"{danger_mod}.{name}" if danger_mod else name
                findings.append(Finding(
                    id=f"F-{next_id:04d}",
                    agent="static_supply",
                    category=FindingCategory.CODE_DANGEROUS_PATTERN,
                    severity=Severity.HIGH,
                    confidence=0.85,
                    message=f"Dangerous call detected: {qual}()",
                    evidence=EvidencePointer(file_path=file_path, line_start=node.lineno),
                ))
                next_id += 1
                break
    return findings, next_id


def _check_obfuscated(tree: ast.AST, file_path: str, next_id: int) -> tuple[list[Finding], int]:
    """Flag the base64.b64decode + exec pattern within the same function/scope."""
    findings: list[Finding] = []
    has_b64_decode = False
    has_exec = False
    b64_line = None
    exec_line = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            mod, name = _qualified_name(node.func)
            if mod == "base64" and name.startswith("b64decode"):
                has_b64_decode = True
                b64_line = node.lineno
            elif name == "exec":
                has_exec = True
                exec_line = node.lineno
    if has_b64_decode and has_exec:
        findings.append(Finding(
            id=f"F-{next_id:04d}",
            agent="static_supply",
            category=FindingCategory.CODE_OBFUSCATED,
            severity=Severity.HIGH,
            confidence=0.7,
            message="Base64 decode + exec pattern detected — likely obfuscated payload.",
            evidence=EvidencePointer(file_path=file_path, line_start=b64_line or exec_line),
        ))
        next_id += 1
    return findings, next_id


def _check_secrets(text: str, file_path: str, next_id: int) -> tuple[list[Finding], int]:
    """Regex-scan source text for hardcoded secrets."""
    findings: list[Finding] = []
    seen_kinds: set[str] = set()
    for pattern, kind in SECRET_PATTERNS:
        m = pattern.search(text)
        if not m or kind in seen_kinds:
            continue
        seen_kinds.add(kind)
        line_no = text[: m.start()].count("\n") + 1
        # Don't leak the actual secret — just first 8 chars + redaction
        excerpt = m.group(0)[:8] + "..." + m.group(0)[-4:]
        findings.append(Finding(
            id=f"F-{next_id:04d}",
            agent="static_supply",
            category=FindingCategory.SECRET_LEAKED,
            severity=Severity.MEDIUM,
            confidence=0.8,
            message=f"Hardcoded {kind} found in source: {excerpt}",
            evidence=EvidencePointer(file_path=file_path, line_start=line_no),
        ))
        next_id += 1
    return findings, next_id


def _check_typosquats(text: str, file_path: str, next_id: int) -> tuple[list[Finding], int]:
    """Scan imports for typosquat-likely names (distance 1-2 from popular)."""
    findings: list[Finding] = []
    import_re = re.compile(r'^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)
    seen: set[str] = set()
    for m in import_re.finditer(text):
        mod = m.group(1).lower().split(".")[0]
        if mod in seen:
            continue
        seen.add(mod)
        if mod in POPULAR_PACKAGES:
            continue
        for popular in POPULAR_PACKAGES:
            d = _levenshtein(mod, popular)
            if 1 <= d <= 2 and len(mod) >= 4:
                line_no = text[: m.start()].count("\n") + 1
                findings.append(Finding(
                    id=f"F-{next_id:04d}",
                    agent="static_supply",
                    category=FindingCategory.TYPOSQUAT_LIKELY,
                    severity=Severity.MEDIUM,
                    confidence=0.75,
                    message=(
                        f"Import {mod!r} is only edit-distance {d} from popular "
                        f"package {popular!r} — possible typosquat."
                    ),
                    evidence=EvidencePointer(file_path=file_path, line_start=line_no),
                    extra={"imported": mod, "near": popular, "distance": str(d)},
                ))
                next_id += 1
                break
    return findings, next_id


class StaticSupplyAgent:
    """AST + regex analysis. Catches dangerous patterns, secrets, typosquats."""

    async def run(self, bundle: "SkillBundle") -> list[Finding]:
        log.info("static.start", extra={"bundle_sha": bundle.bundle_sha})

        if bundle.root_path is None:
            return []

        findings: list[Finding] = []
        next_id = 1

        for f in bundle.files:
            if not f.path.endswith(".py"):
                continue
            full = bundle.root_path / f.path
            try:
                text = full.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (OSError, SyntaxError) as exc:
                log.debug("static.skip %s: %s", f.path, exc)
                continue

            new, next_id = _check_dangerous_ast(tree, f.path, next_id)
            findings.extend(new)
            new, next_id = _check_obfuscated(tree, f.path, next_id)
            findings.extend(new)
            new, next_id = _check_secrets(text, f.path, next_id)
            findings.extend(new)
            new, next_id = _check_typosquats(text, f.path, next_id)
            findings.extend(new)

        log.info(
            "static.done",
            extra={"bundle_sha": bundle.bundle_sha, "n_findings": len(findings)},
        )
        return findings

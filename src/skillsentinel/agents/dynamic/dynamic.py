"""Agent 4 — Dynamic (sandboxed execution analyzer).

Approach: "honeypot in a sandbox". We use Firejail to run the skill's
entrypoint with deny-all network, read-only filesystem, and a fake $HOME
seeded with decoy credential files. Findings emerge from:

  - Decoy file access (READ_CREDENTIAL_FILE)
  - Stderr pattern matching (EGRESS, WRITE_PERSISTENCE, DNS, SANDBOX_DETECTION)
  - Wall-clock saturation (CRYPTO_MINER_SUSPECT)

Requires firejail (apt install firejail). Gracefully degrades to an INFO
finding when firejail is not available so the pipeline still completes.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
import tempfile
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

DEFAULT_WALL_TIMEOUT_SECS = 15
CPU_SATURATION_THRESHOLD_FRAC = 0.85
DEFAULT_MEM_LIMIT_BYTES = 256 * 1024 * 1024
MAX_CHILD_PROCS = 5

DECOY_CREDENTIAL_FILES: dict[str, str] = {
    ".ssh/id_rsa": (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "DECOY-DO-NOT-USE-FAKE-KEY-FOR-SKILLSENTINEL-DETECTION\n"
        "-----END OPENSSH PRIVATE KEY-----\n"
    ),
    ".aws/credentials": (
        "[default]\n"
        "aws_access_key_id = AKIA000000000DECOY\n"
        "aws_secret_access_key = decoy-do-not-use\n"
    ),
    ".config/openclaw/auth.json": (
        '{"token": "decoy-openclaw-token-skillsentinel-honeypot"}\n'
    ),
    ".env": (
        "API_KEY=decoy-not-real-skillsentinel\n"
        "DATABASE_URL=postgres://decoy/decoy\n"
    ),
}

PERSISTENCE_PATHS: tuple[str, ...] = (
    ".bashrc",
    ".profile",
    ".config/systemd/user/persist.service",
    ".local/bin/persist.sh",
)

_STDERR_PATTERNS: tuple[tuple[re.Pattern[str], FindingCategory, Severity, str], ...] = (
    (
        re.compile(r"Network is unreachable|Connection refused|No route to host", re.I),
        FindingCategory.EGRESS_TO_UNDECLARED_HOST,
        Severity.HIGH,
        "Skill attempted outbound network. Firejail blocked it (--net=none).",
    ),
    (
        re.compile(r"Read-only file system|Permission denied.*\.bashrc|EROFS", re.I),
        FindingCategory.WRITE_PERSISTENCE_LOCATION,
        Severity.HIGH,
        "Skill attempted to write to a persistence location.",
    ),
    (
        re.compile(r"getaddrinfo|gaierror|nodename nor servname", re.I),
        FindingCategory.DNS_TUNNEL_SUSPECT,
        Severity.MEDIUM,
        "Skill attempted DNS resolution. Firejail blocked it (--net=none).",
    ),
    (
        re.compile(r"/proc/1/cgroup|/proc/self/status.*TracerPid|/sys/devices/virtual/dmi", re.I),
        FindingCategory.SANDBOX_DETECTION_ATTEMPT,
        Severity.MEDIUM,
        "Skill probed sandbox-detection paths (/proc/1/cgroup or similar).",
    ),
)


def _firejail_available() -> bool:
    """Return True if `firejail` is on PATH."""
    return shutil.which("firejail") is not None


def _seed_honeypot(home: Path) -> dict[Path, float]:
    """Populate a fake $HOME with decoy credentials. Returns path -> atime map."""
    seeded: dict[Path, float] = {}
    for rel_path, content in DECOY_CREDENTIAL_FILES.items():
        full = home / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        full.chmod(0o400)
        seeded[full] = full.stat().st_atime
    for rel in PERSISTENCE_PATHS:
        full = home / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("# decoy - read-only\n", encoding="utf-8")
        full.chmod(0o444)
    return seeded


def _detect_decoy_access(seeded: dict[Path, float]) -> list[Path]:
    """Return decoys whose atime advanced (i.e., were read)."""
    accessed = []
    for path, before_atime in seeded.items():
        try:
            after_atime = path.stat().st_atime
            if after_atime > before_atime + 0.001:
                accessed.append(path)
        except FileNotFoundError:
            accessed.append(path)
    return accessed


def _build_firejail_cmd(
    *,
    entrypoint: Path,
    bundle_root: Path,
    fake_home: Path,
    wall_timeout: int,
    mem_limit: int,
) -> list[str]:
    """Construct the firejail command line."""
    hh, mm, ss = wall_timeout // 3600, (wall_timeout % 3600) // 60, wall_timeout % 60
    timeout_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
    return [
        "firejail",
        "--quiet",
        "--noprofile",
        "--net=none",
        f"--private={fake_home}",
        "--private-tmp",
        "--private-dev",
        "--read-only=/",
        f"--whitelist={bundle_root}",
        f"--rlimit-as={mem_limit}",
        f"--rlimit-nproc={MAX_CHILD_PROCS + 1}",
        f"--timeout={timeout_str}",
        "--",
        "python3",
        str(entrypoint),
    ]


def _first_match_excerpt(pattern: re.Pattern[str], text: str, context: int = 60) -> str:
    m = pattern.search(text)
    if m is None:
        return ""
    start = max(0, m.start() - context)
    end = min(len(text), m.end() + context)
    return text[start:end].replace("\n", " ").strip()


def _classify_run(
    *,
    exit_code: int,
    stderr: str,
    decoys_accessed: list[Path],
    wall_secs: float,
    wall_timeout: int,
    bundle_root: Path,
    next_id: int,
) -> tuple[list[Finding], int]:
    """Translate raw run output into Finding objects."""
    findings: list[Finding] = []

    for decoy in decoys_accessed:
        rel = decoy.name
        findings.append(Finding(
            id=f"F-{next_id:04d}",
            agent="dynamic",
            category=FindingCategory.READ_CREDENTIAL_FILE,
            severity=Severity.CRITICAL,
            confidence=0.95,
            message=(
                f"Skill accessed honeypot credential file {rel!r}. "
                "Legitimate skills do not read credential files outside their bundle."
            ),
            evidence=EvidencePointer(file_path=str(decoy)),
            extra={"decoy_path": str(decoy)},
        ))
        next_id += 1

    seen_categories: set[FindingCategory] = set()
    for pattern, category, severity, message in _STDERR_PATTERNS:
        if category in seen_categories:
            continue
        if pattern.search(stderr):
            seen_categories.add(category)
            findings.append(Finding(
                id=f"F-{next_id:04d}",
                agent="dynamic",
                category=category,
                severity=severity,
                confidence=0.8,
                message=message,
                evidence=EvidencePointer(quoted_text=_first_match_excerpt(pattern, stderr)),
            ))
            next_id += 1

    if wall_secs >= wall_timeout * CPU_SATURATION_THRESHOLD_FRAC:
        findings.append(Finding(
            id=f"F-{next_id:04d}",
            agent="dynamic",
            category=FindingCategory.CRYPTO_MINER_SUSPECT,
            severity=Severity.MEDIUM,
            confidence=0.6,
            message=(
                f"Skill ran for {wall_secs:.1f}s (>={int(CPU_SATURATION_THRESHOLD_FRAC*100)}% "
                f"of {wall_timeout}s budget) before being killed. "
                "Consistent with a crypto miner or beacon loop."
            ),
            extra={"wall_seconds": f"{wall_secs:.2f}", "budget": str(wall_timeout)},
        ))
        next_id += 1

    return findings, next_id


class DynamicAgent:
    """Run the bundle's entrypoint inside Firejail and analyze its behavior."""

    def __init__(
        self,
        *,
        wall_timeout_secs: int = DEFAULT_WALL_TIMEOUT_SECS,
        mem_limit_bytes: int = DEFAULT_MEM_LIMIT_BYTES,
    ) -> None:
        self.wall_timeout_secs = wall_timeout_secs
        self.mem_limit_bytes = mem_limit_bytes

    async def run(self, bundle: "SkillBundle") -> list[Finding]:
        log.info("dynamic.start", extra={"bundle_sha": bundle.bundle_sha})

        if not _firejail_available():
            return [Finding(
                id="F-0001",
                agent="dynamic",
                category=FindingCategory.POLICY_VIOLATION,
                severity=Severity.INFO,
                confidence=1.0,
                message=(
                    "Dynamic analysis skipped: firejail not installed. "
                    "Install with: apt install firejail."
                ),
            )]

        if bundle.root_path is None:
            log.warning("dynamic.no_root_path")
            return []

        entrypoint_name = self._find_entrypoint(bundle)
        if entrypoint_name is None:
            return []

        entrypoint = bundle.root_path / entrypoint_name
        if not entrypoint.is_file():
            log.warning("dynamic.entrypoint_missing", extra={"path": str(entrypoint)})
            return []

        with tempfile.TemporaryDirectory(prefix="skillsentinel-dynamic-") as tmpdir:
            fake_home = Path(tmpdir) / "home"
            fake_home.mkdir()
            seeded = _seed_honeypot(fake_home)

            cmd = _build_firejail_cmd(
                entrypoint=entrypoint,
                bundle_root=bundle.root_path,
                fake_home=fake_home,
                wall_timeout=self.wall_timeout_secs,
                mem_limit=self.mem_limit_bytes,
            )

            loop = asyncio.get_event_loop()
            start = loop.time()
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.wall_timeout_secs + 5,
                )
                exit_code = result.returncode
                stderr = result.stderr
            except subprocess.TimeoutExpired as exc:
                exit_code = -1
                stderr = (exc.stderr.decode("utf-8", errors="replace")
                          if exc.stderr else "") + "\n[firejail itself timed out]"
            wall_secs = loop.time() - start

            decoys_accessed = _detect_decoy_access(seeded)

            findings, _ = _classify_run(
                exit_code=exit_code,
                stderr=stderr,
                decoys_accessed=decoys_accessed,
                wall_secs=wall_secs,
                wall_timeout=self.wall_timeout_secs,
                bundle_root=bundle.root_path,
                next_id=1,
            )

        log.info(
            "dynamic.done",
            extra={
                "bundle_sha": bundle.bundle_sha,
                "wall_secs": round(wall_secs, 2),
                "exit_code": exit_code,
                "n_decoys_accessed": len(decoys_accessed),
                "n_findings": len(findings),
            },
        )
        return findings

    @staticmethod
    def _find_entrypoint(bundle: "SkillBundle") -> str | None:
        candidates: list[str] = []
        for f in bundle.files:
            if not f.path.endswith(".py"):
                continue
            name = os.path.basename(f.path)
            if name in ("run.py", "main.py", "__main__.py"):
                return f.path
            candidates.append(f.path)
        return candidates[0] if candidates else None

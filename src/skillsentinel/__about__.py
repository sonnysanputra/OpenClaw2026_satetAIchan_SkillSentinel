"""Build provenance.

Two build modes:

* **Internal builds** (default, for the team) expose the full version, build date,
  and git SHA via ``--version`` and structured logs.
* **Public builds** (``SKILLSENTINEL_PUBLIC_BUILD=1``) strip these so adversaries
  scanning a skill cannot detect which scanner version is running.

In CI, ``scripts/build_info.py`` overwrites this file from ``git describe``
before packaging. The values committed here are placeholders.
"""

from __future__ import annotations

import os

# These three constants are overwritten by scripts/build_info.py during CI builds.
__version__ = "0.1.0a1"  # PEP 440 form; git tag is v0.1.0-foundations
__build_date__ = "1970-01-01T00:00:00Z"
__git_sha__ = "unknown"

# Public mode: redact everything an adversary could fingerprint.
_PUBLIC_MODE = os.environ.get("SKILLSENTINEL_PUBLIC_BUILD") == "1"

if _PUBLIC_MODE:
    __version__ = "SkillSentinel"
    __build_date__ = ""
    __git_sha__ = ""


def version_string(verbose: bool = False) -> str:
    """Return a human-readable version banner."""
    if _PUBLIC_MODE:
        return "SkillSentinel"
    if not verbose:
        return f"SkillSentinel {__version__}"
    return (
        f"SkillSentinel {__version__}\n"
        f"  Built:   {__build_date__}\n"
        f"  Commit:  {__git_sha__}"
    )

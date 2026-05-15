#!/usr/bin/env python3
"""Load and validate the SkillSentinel labeled corpus.

Usage:
    python scripts/corpus_loader.py            # validate and print stats
    python scripts/corpus_loader.py --json     # emit one JSON summary

Exits non-zero if validation fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_ROOT = REPO_ROOT / "corpus"
LABELS_FILE = CORPUS_ROOT / "labels.jsonl"


@dataclass
class CorpusEntry:
    path: Path
    label: str
    categories: list[str]
    source: str
    labeler: str


def load_entries() -> list[CorpusEntry]:
    if not LABELS_FILE.exists():
        sys.exit(f"labels.jsonl not found at {LABELS_FILE}")

    entries: list[CorpusEntry] = []
    for n, line in enumerate(LABELS_FILE.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            sys.exit(f"line {n}: invalid JSON: {e}")
        path = CORPUS_ROOT / rec["path"]
        entries.append(
            CorpusEntry(
                path=path,
                label=rec["label"],
                categories=rec.get("categories", []),
                source=rec.get("source", "unknown"),
                labeler=rec.get("labeler", "unknown"),
            )
        )
    return entries


def validate(entries: list[CorpusEntry]) -> list[str]:
    """Return a list of validation errors (empty if all good)."""
    errors: list[str] = []
    for e in entries:
        if not e.path.is_dir():
            errors.append(f"{e.path}: directory missing")
            continue
        for required in ("skill.yaml", "run.py", "meta.json"):
            if not (e.path / required).is_file():
                errors.append(f"{e.path}: missing {required}")
        if e.label not in ("malicious", "benign"):
            errors.append(f"{e.path}: invalid label {e.label!r}")
        if e.label == "malicious" and not e.categories:
            errors.append(f"{e.path}: malicious entries must declare categories")
    return errors


def stats(entries: list[CorpusEntry]) -> dict:
    label_counts = Counter(e.label for e in entries)
    cat_counts: Counter = Counter()
    for e in entries:
        cat_counts.update(e.categories)
    return {
        "total": len(entries),
        "by_label": dict(label_counts),
        "by_category": dict(cat_counts),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Emit a single JSON summary.")
    args = parser.parse_args()

    entries = load_entries()
    errors = validate(entries)
    summary = stats(entries)

    if args.json:
        out = {"ok": not errors, "errors": errors, "stats": summary}
        print(json.dumps(out, indent=2))
        return 0 if not errors else 1

    print(f"Loaded {summary['total']} entries.")
    print(f"  Labels: {summary['by_label']}")
    print(f"  Categories: {summary['by_category']}")

    if errors:
        print("\nValidation errors:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nAll entries valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

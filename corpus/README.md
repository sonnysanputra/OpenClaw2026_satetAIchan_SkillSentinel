# Corpus

The labeled corpus of skill samples. See `docs/skill_sentinel_test_plan.md` §2 for the building strategy.

Layout:

- `malicious/` — known-malicious samples, one folder per skill.
- `benign/` — known-benign samples, one folder per skill.
- `labels.jsonl` — one JSON per line: `{path, label, categories, source, labeler}`.

Phase 1 starts when there are 10 hand-crafted malicious and 10 hand-crafted benign samples here.

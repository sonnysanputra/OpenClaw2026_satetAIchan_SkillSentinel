# SkillSentinel

A multi-agent security system that vets AI agent skills before they are installed into an agent host (OpenClaw, Claude Code, Cowork, AutoGen, …). Five specialist agents — structural, static, semantic, dynamic, adjudicative — produce a signed verdict and a continuously-monitored installation.

## Status

This is **Phase 0 — Foundations**. The orchestrator wires five empty agents end-to-end; detection logic arrives in Phases 1–3. See `docs/skill_sentinel_todo_list.md` for the complete development plan.

## Quick start

```bash
# Install dependencies (using uv — recommended)
uv sync

# Or using pip
pip install -e ".[dev]"

# Run the scanner on a dummy bundle
python -m skillsentinel scan ./some-skill-bundle/

# Run the test suite
pytest

# Lint and type-check
ruff check .
mypy src/
```

## Architecture

See `docs/skill_sentinel_design.md` for the full architecture. Briefly:

```
Intake → [ Static & Supply-Chain  |  Semantic  |  Dynamic Behavior ] → Verdict
   (parsing/manifest)   (Semgrep/CVE/IOC)   (LLM)    (sandbox)    (policy/score/sign)
```

## Repository layout

```
skillsentinel/
├── src/skillsentinel/
│   ├── shared/             # Pydantic schemas shared across agents
│   ├── orchestrator/       # Thin coordinator that wires agents together
│   ├── agents/             # Five specialist agents
│   │   ├── intake/
│   │   ├── static_supply/
│   │   ├── semantic/
│   │   ├── dynamic/
│   │   └── verdict/
│   ├── cli/                # `skillsentinel` command-line entry point
│   └── daemon/             # Long-running gateway (Phase 3)
├── tests/                  # pytest test suite
├── corpus/                 # Labeled skill samples (Phase 1+)
├── policies/               # OPA / Rego policy packs (Phase 3)
├── scripts/                # Build and utility scripts
└── docs/                   # Design docs and roadmaps
```

## Contributing

Conventional commits required (`feat:`, `fix:`, `docs:`, `chore:`, `test:`). Branch protection on `main` requires PR review + green CI.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Security

This project is itself security-sensitive. Do not file public issues for vulnerabilities; contact the maintainers privately.

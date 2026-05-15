# Phase 0 Setup Guide

This document walks you (and your three teammates) through getting the SkillSentinel scaffold running end-to-end. It should take ~10 minutes on a fresh machine.

---

## 1. Create the GitHub repo (Sonny — Task #1)

1. Go to `https://github.com/new`.
2. Repository name: `skillsentinel` (private for now).
3. Don't initialize with a README, .gitignore, or license — this scaffold has them.
4. **Settings → Branches → Add rule:** branch name `main`, require PR review + require status checks ("CI") to pass.
5. **Settings → Collaborators:** add the other three teammates.

## 2. Clone and drop the scaffold in

```bash
git clone git@github.com:<your-org>/skillsentinel.git
cd skillsentinel

# Copy the contents of this `skillsentinel/` folder from outputs/
# into the cloned directory. (On Windows, copy with Explorer or
# `xcopy /E /I`; on macOS/Linux: `cp -R <outputs>/skillsentinel/. .`)

git add .
git commit -m "feat: initial scaffold (Phase 0)"
git tag -s v0.1.0-foundations -m "Phase 0 close — foundations"
git push -u origin main
git push --tags
```

(If you don't have a signing key yet: `gpg --gen-key`, then `git config --global user.signingkey <KEY-ID>` and `git config --global commit.gpgsign true`.)

## 3. Install dependencies

You need Python 3.12+. Two options:

### Option A — uv (recommended, fast)

```bash
# Install uv first if you don't have it.
curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync --all-extras
```

### Option B — pip + venv

```bash
python3.12 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -e ".[dev,gateway]"
```

## 4. Install pre-commit hooks

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

## 5. Smoke-test the scaffold

```bash
# Generate __about__.py from current git state.
make build-info

# Lint, type-check, test.
make ci

# End-to-end scan of an empty bundle (uses stub agents).
mkdir -p /tmp/dummy-skill
echo "name: dummy" > /tmp/dummy-skill/skill.yaml
python -m skillsentinel scan /tmp/dummy-skill --no-dynamic
```

Expected output: a green ALLOW verdict with no findings and a "Phase-0 stub" justification.

## 6. Verify CI runs

Push a tiny PR (e.g., update `AUTHORS.md` with your name). Confirm the CI workflow passes. Once merged, you're ready for Phase 1.

---

## Who owns what going into Phase 1

| Agent | Owner | Shipped scope |
|---|---|---|
| Agent 1 — Intake | Sonny Sanputra | OpenClaw / Claude Code / MCP bundle parser, SHA-256 file indexing, manifest schema validation, canonical `SkillBundle` construction with early findings for malformed or over-broad manifests |
| Agent 2 — Static & Supply-Chain | Brandon Go | AST-based detection of dangerous calls (`eval`, `exec`, `pickle.loads`, `subprocess(shell=True)`), secret-pattern regex (AWS, GitHub, OpenAI, Slack tokens with auto-redaction), Levenshtein typosquat scoring against the top 10k packages |
| Agent 3 — Semantic | Justin Stevenson Theodorus | LLM-based intent analyzer via Claude Sonnet 4.6 with strict structured-output JSON; diffs the publisher's manifest description against the actual code behavior, detects prompt-injection / META instruction-override / obfuscation; graceful fall-back when the API key is unset |
| Agent 4 — Dynamic | Rendi Fuji Wikarta | Firejail sandbox (`--net=none`, `--read-only=/`, `--private`) with a seeded honeypot home (`~/.ssh/id_rsa`, `~/.aws/credentials`, `~/.config/openclaw/auth.json`, `~/.env`); file `atime` tracking for decoy reads; stderr pattern classification for egress / persistence / DNS / sandbox-escape; CPU-saturation flag for crypto-miner suspects |
| Agent 5 — Verdict + Corpus | Sonny Sanputra | Pure-Python deterministic risk scoring (severity × confidence × category multiplier, clamped 0–100), signed `policy_hash` for auditability, 4-state verdict (ALLOW / WARN / REVIEW / BLOCK) with one-sentence justification; 10-skill hand-crafted labeled corpus (5 benign, 5 malicious) |

Everyone is also responsible for tests in their agent. Pair occasionally so no one is the only person who understands a subsystem.

---

## When you hit problems

- `make ci` is your local mirror of CI. Run it before pushing.
- Conventional-commits is enforced by CI. Format: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`.
- Branch protection is on; everything goes through PR. One reviewer minimum.
- For design discussions, open a GitHub Discussion before writing code.

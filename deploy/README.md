# SkillSentinel — Deployment Artifacts

Each subdirectory mirrors an OpenClaw skill folder that gets copied to
`/usr/lib/node_modules/openclaw/skills/<name>/` on the host.

## Layout

```
deploy/
├── README.md                 (this file)
├── deploy.sh                 (one-shot sync script)
├── skillsentinel-intake/
│   ├── SKILL.md              OpenClaw skill manifest
│   └── intake.py             Thin wrapper around IntakeAgent
└── skillsentinel-dynamic/
    ├── SKILL.md
    └── dynamic.py
```

## Deploying

On the droplet, after `git pull`:

```bash
sudo bash deploy/deploy.sh
```

Then clear the agent's session cache + restart so the new skills appear in
`<available_skills>`:

```bash
rm -f /root/.openclaw/agents/main/sessions/*.jsonl*
rm -f /root/.openclaw/agents/main/sessions/*.json
openclaw gateway restart
```

## Verifying

```bash
openclaw skills check --agent main | grep -i skillsentinel
openclaw agent --agent main --local --message "Use the skillsentinel-intake skill to scan /opt/skillsentinel/corpus/malicious/03-typosquat-dependency"
```

The agent should pick up the skill and post embeds to your Discord channel
(configured via `SKILLSENTINEL_DISCORD_WEBHOOK` env var).

# SkillSentinel

A multi-agent security gateway that vets AI agent skills before they are installed into an agent host. Every skill passes through a five-agent analysis pipeline — structural, static, semantic, dynamic, and adjudicative — producing a signed `APPROVED` or `BLOCKED` verdict before anything touches your server.

Built for the **OpenClaw 2026** hackathon. Includes a full-stack **Agent Builder** web app for configuring and deploying OpenClaw agents with security baked in by default.

## How it works

```
Intake → Static & Supply-Chain → Semantic → Dynamic (Sandbox) → Verdict
  │             │                    │              │               │
manifest     Semgrep +            LLM intent     firejail +     OPA/Rego
 parsing     CVE/IOC               analysis      honeypot       + signed
                                                 $HOME          verdict
```

The gateway **fails closed** — any error or ambiguous result returns `BLOCKED`.

---

## Agent Builder — Web App

The `builder/` directory contains a full-stack web app (Next.js 14 + FastAPI) with a guided 9-step wizard for configuring and deploying an OpenClaw agent to a remote VPS. Every skill selected in the wizard is routed through the SkillSentinel security gateway for review before installation is allowed.

### Prerequisites

Before opening the app, make sure you have the following ready:

- A **Linux VPS** (Ubuntu 22.04 recommended) reachable over the internet
- **SSH access** configured on the VPS — either a private key or a password
- Port 22 open on the VPS firewall (or whichever port SSH is running on)
- An **API key** for your chosen LLM provider (Anthropic, OpenAI, Gemini, etc.), unless you use Ollama
- Credentials for whichever **messaging channel** you want the agent to use (see channel guide below)
- A running **SkillSentinel / OpenClaw gateway** instance with its URL and token (needed for skill security review)

### Starting the servers

You need two terminals — one for the backend and one for the frontend.

**Terminal 1 — Backend (FastAPI)**

```bash
cd builder/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and fill in:

| Variable | What to put |
|----------|-------------|
| `SECURITY_GATEWAY_URL` | WebSocket URL of your OpenClaw/SkillSentinel gateway, e.g. `wss://your-gateway-host:18789` |
| `SECURITY_GATEWAY_TOKEN` | The shared-secret token for that gateway |
| `SECURITY_AGENT_SESSION` | Session key for the security agent, e.g. `agent:security:main` |
| `SECURITY_GATEWAY_LOOPBACK` | Set `true` if the gateway is running on the same host as the backend |
| `FRONTEND_ORIGIN` | Leave as `http://localhost:3000` for local dev |

Then start the backend:

```bash
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend (Next.js)**

```bash
cd builder/frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

---

### Wizard walkthrough

The wizard has 9 steps. Work through them in order — the **Next** button stays disabled until the current step is valid.

---

#### Step 1 — VPS access

Enter the SSH connection details for the server where the agent will be installed.

| Field | Notes |
|-------|-------|
| Host or IP | Public IP or hostname of your VPS |
| User | SSH user, typically `ubuntu`, `root`, or `debian` |
| Port | Default is `22` |
| Auth method | Choose **SSH key** (recommended) or **Password** |
| Private key | Paste the full contents of your private key file, e.g. `~/.ssh/id_ed25519` |

> **Warning:** Make sure port 22 (or your custom SSH port) is open in your VPS firewall/security group before testing. A timeout here means the port is blocked, not that the credentials are wrong.

Click **Test connection** before proceeding. The button will confirm the OS and whether OpenClaw is already installed.

> **Warning:** The private key is sent to the backend over localhost only — it is not stored and never leaves your machine during local dev. Do not use this wizard over an untrusted network without TLS.

---

#### Step 2 — Agent identity

Give your agent a name and a workspace location on the VPS.

| Field | Notes |
|-------|-------|
| Display name | Human-readable name, e.g. `Aria` |
| Slug | Auto-derived from the name, used in file paths and the agent ID |
| Emoji | Decorative — shown in the agent's persona files |
| Theme | Optional tone descriptor, e.g. `midnight-orange` |
| Workspace path | Where files are written on the VPS — defaults to `~/.openclaw/workspace-<slug>` |

---

#### Step 3 — Persona

Define the agent's behavioral style.

- **Tone** — e.g. Friendly, Professional, Direct
- **Traits** — short descriptors like `concise`, `proactive`
- **Avoid** — hard limits written into the agent's SOUL.md, e.g. `"Never share private keys"`

---

#### Step 4 — Instructions

Describe what the agent should do in plain language.

- **Responsibilities** — tasks the agent performs, e.g. `"Research the web and summarize daily briefings"`
- **Security rules** — toggle on to auto-include a standard safety policy

---

#### Step 5 — Model

Pick the LLM provider and model. An API key is required for all providers except Ollama.

| Provider | Where to get an API key |
|----------|------------------------|
| Anthropic | console.anthropic.com |
| OpenAI | platform.openai.com |
| Gemini | aistudio.google.com |
| OpenRouter | openrouter.ai |
| Ollama | No key needed — must be running locally on the VPS |

The optional **heartbeat model** is used for lightweight keep-alive pings and can be a cheaper/faster model than the primary.

---

#### Step 6 — Channels

Choose which messaging platforms the agent will listen on and provide the required credentials. You must set up a bot on each platform before filling in this step.

**Telegram** (Easy)
- Create a bot via [@BotFather](https://t.me/botfather) on Telegram
- Copy the bot token it gives you (format: `1234567890:ABCdef...`)

**Discord** (Easy)
- Go to the [Discord Developer Portal](https://discord.com/developers/applications) → New Application → Bot
- Copy the **Bot Token**
- Enable **Message Content Intent** under Bot → Privileged Gateway Intents
- Add the bot to your server and get the **Server ID** and **Channel ID** by enabling Developer Mode in Discord settings, then right-clicking the server/channel

**Slack** (Medium)
- Create an app at [api.slack.com/apps](https://api.slack.com/apps)
- Install it to your workspace to get the **Bot Token** (`xoxb-...`)
- Under Socket Mode, generate an **App Token** (`xapp-...`)
- The **Channel ID** is optional — visible by right-clicking a channel in Slack

**WhatsApp** (Medium)
- Requires a [Meta Developer](https://developers.facebook.com) account and a WhatsApp Business app
- **Phone Number ID** and **Access Token** come from the app dashboard
- **Webhook Verify Token** is a string you choose — used to validate incoming webhooks from Meta

**Signal** (Advanced)
- Requires [signal-cli](https://github.com/AsamK/signal-cli) running on the VPS
- Enter the phone number linked to your Signal account

**iMessage** (Mac only)
- Requires the agent to be deployed on a Mac with iMessage signed in
- Enter the Apple ID associated with that Mac

**LINE** (Medium)
- Create a Messaging API channel in the [LINE Developers Console](https://developers.line.biz)
- Copy the **Channel Access Token** and **Channel Secret**

**Matrix** (Advanced)
- You need a Matrix account on a homeserver
- **Homeserver URL** — e.g. `https://matrix.org`
- **Access Token** — get it from Element → Settings → Help & About → Access Token
- **Room ID** — visible in the room settings under Advanced, format `!roomid:server`

---

#### Step 7 — Skills

Browse the community skill catalogue and add skills to your agent. This is where SkillSentinel kicks in.

When you click **Add** on a skill:
1. The backend fetches the skill's SKILL.md from the catalogue
2. It sends the content to the SkillSentinel security gateway
3. The gateway runs the skill through the five-agent pipeline
4. The result appears as a live badge:
   - **APPROVED** (green) — skill is safe to install
   - **BLOCKED** (red) — skill was rejected; the reason is shown inline

> **Warning:** Blocked skills cannot be added. The verdict is final — the gateway fails closed, meaning any ambiguous result also returns BLOCKED.

---

#### Step 8 — User context

Optional free-text field for background context about the operator. This is written into the agent's USER.md file on the VPS and gives the agent more situational awareness.

---

#### Step 9 — Review & deploy

Shows a summary of all configuration and previews the generated files (`SOUL.md`, `AGENTS.md`, `IDENTITY.md`, `USER.md`) that will be written to the VPS.

Click **Deploy** to:
1. SSH into the VPS
2. Create the workspace directory
3. Write all config files
4. Install each approved skill
5. Register and start the OpenClaw runtime

A live log streams back to the browser. When complete, the agent ID and workspace path are shown. Send the agent a first message on your chosen channel to wake it up.

> **Warning:** Deploy is not reversible from the UI. To remove an agent, SSH into the VPS and delete the workspace directory manually.

---

## SkillSentinel scanner (CLI)

```bash
# Install dependencies (uv recommended)
uv sync

# Or pip
pip install -e ".[dev]"

# Scan a skill bundle
python -m skillsentinel scan ./some-skill-bundle/

# Run tests
pytest

# Lint and type-check
ruff check .
mypy src/
```

---

## Repository layout

```
├── src/skillsentinel/
│   ├── agents/
│   │   ├── intake/          manifest parsing + bundle validation
│   │   ├── static_supply/   Semgrep, CVE lookup, IOC matching
│   │   ├── semantic/        LLM-powered intent analysis (Claude)
│   │   ├── dynamic/         firejail sandbox + honeypot $HOME
│   │   └── verdict/         score aggregation, OPA/Rego, signed verdict
│   ├── orchestrator/        wires agents end-to-end
│   ├── shared/              Pydantic schemas shared across agents
│   ├── cli/                 `skillsentinel` CLI entry point
│   └── daemon/              long-running gateway mode (Phase 3)
├── builder/                 Agent Builder web app (Next.js + FastAPI)
├── tests/                   pytest test suite
├── corpus/                  labeled skill samples
├── policies/                OPA / Rego policy packs
├── scripts/                 build and utility scripts
└── docs/                    design docs and roadmaps
```

## Roadmap

| Phase | Focus |
|-------|-------|
| 0 — Foundations (current) | Five-agent pipeline wired end-to-end; Agent Builder deployed |
| 1 — Detection | Semgrep rules, CVE database, IOC lists live in Static agent |
| 2 — Semantic corpus | Labeled malicious skill samples; tuned verdict scoring |
| 3 — Runtime monitoring | Daemon mode — continuous post-install behavioral monitoring |

## Team

| Name | Role |
|------|------|
| Sonny Sanputra | Project lead, architecture |
| Brandon Go | Member |
| Justin Stevenson Theodorus | Member |
| Rendi Fuji Wikarta | Member |

## Contributing

Conventional commits required (`feat:`, `fix:`, `docs:`, `chore:`, `test:`). Branch protection on `main` requires PR review + green CI.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Security

This project is itself security-sensitive. Do not file public issues for vulnerabilities; contact the maintainers privately.

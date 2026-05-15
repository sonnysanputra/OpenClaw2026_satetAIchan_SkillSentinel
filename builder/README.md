# OpenClaw Agent Builder

A full-stack web app for configuring, deploying, and securing an OpenClaw agent on a remote VPS — with a guided wizard UI and an automated security gate that routes every selected skill through a running [SkillsSentinel](../SkillsSentinel) instance for review before installation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Next.js 14 Frontend (App Router)                │
│  Wizard UI → SkillsHub Browser → Security Review → Deploy   │
└────────────────────────┬────────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                FastAPI Backend (Python 3.11+)                │
│  File Gen ·  Security Gateway WS Client ·  paramiko SSH     │
└──────────┬──────────────────────────────────┬───────────────┘
           │ Gateway WS protocol v3           │ SSH
   ┌───────▼─────────┐                ┌───────▼───────────┐
   │ Security        │                │ User's VPS        │
   │ OpenClaw / SS   │                │ (OpenClaw agent   │
   │ Gateway         │                │  installs here)   │
   └─────────────────┘                └───────────────────┘
```

## Quick start

The easiest way to start both the frontend and backend simultaneously is using the root `Makefile`:

```bash
cd ..
make run-builder
```

Alternatively, you can run them manually in separate terminals:

```bash
# Backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in SECURITY_GATEWAY_URL + SECURITY_GATEWAY_TOKEN
uvicorn main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev    # http://localhost:3000
```

## Layout

```
openclaw-agent-builder/
├── backend/             FastAPI + paramiko + websockets
│   ├── main.py
│   ├── core/            config + in-memory session store
│   ├── routers/         ssh · skills · deploy · files · ws
│   ├── services/        file_generator · security_gateway · ssh_deployment · skillshub
│   └── schemas/         Pydantic models (PRD §8.3)
└── frontend/            Next.js 14 + Tailwind + shadcn/ui + Zustand
    ├── src/app/         routes (/, /deploy/[id])
    ├── src/components/  wizard steps + skill panels + deploy
    ├── src/store/       wizard.ts (Zustand)
    └── src/lib/         api client, utils
```

## Security Gateway protocol

The backend talks to the SkillsSentinel security agent over the OpenClaw Gateway WebSocket protocol v3:

- **Handshake:** server sends `connect.challenge`; client replies with a `connect` req carrying role `operator`, scopes `["operator.read","operator.write"]`, and a shared-secret token.
- **Skill review:** client sends a `chat.send` RPC targeting the security agent's session key with the skill content embedded in a structured prompt. It collects `chat` / `session.message` events back, then parses `APPROVED` or `BLOCKED: <reason>` from the assistant text.
- **Loopback path:** for same-host gateways, the backend identifies as `client.id: "gateway-client", client.mode: "backend"`, which skips device signing per the gateway docs.

See `backend/services/security_gateway.py` for the implementation.

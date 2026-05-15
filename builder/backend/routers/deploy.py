"""POST /api/deploy — kicks off a background deploy task keyed by session_id."""
from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter

from core.sessions import sessions
from schemas.models import DeployRequest, DeployResponse
from services.ssh_deployment import SshDeployer

router = APIRouter()
log = logging.getLogger(__name__)


@router.post("/deploy", response_model=DeployResponse)
async def start_deploy(req: DeployRequest) -> DeployResponse:
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "request": req,
        "logs": [],
        "status": "pending",
        "ws": None,
    }
    asyncio.create_task(_run_deploy(session_id))
    return DeployResponse(session_id=session_id)


async def _run_deploy(session_id: str) -> None:
    session = sessions.get(session_id)
    if not session:
        return
    session["status"] = "deploying"

    async def emit(level: str, message: str) -> None:
        frame = {"type": "log", "level": level, "message": message}
        session["logs"].append(frame)
        ws = session.get("ws")
        if ws is not None:
            try:
                await ws.send_json(frame)
            except Exception:  # pragma: no cover
                log.exception("Failed to push log to ws for %s", session_id)

    try:
        deployer = SshDeployer(session["request"], emit)
        ok = await deployer.deploy()
    except Exception as e:  # pragma: no cover - defensive
        log.exception("Deploy crashed for %s", session_id)
        await emit("error", f"Deployment crashed: {e}")
        ok = False

    final = "completed" if ok else "failed"
    session["status"] = final
    ws = session.get("ws")
    if ws is not None:
        try:
            await ws.send_json({"type": "status", "status": final})
        except Exception:
            pass

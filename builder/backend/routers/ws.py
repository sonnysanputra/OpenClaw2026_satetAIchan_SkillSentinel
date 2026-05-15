"""WebSocket /ws/deploy/{session_id} — streams deploy logs to the frontend."""
from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.sessions import sessions

router = APIRouter()
log = logging.getLogger(__name__)


@router.websocket("/ws/deploy/{session_id}")
async def deploy_ws(websocket: WebSocket, session_id: str) -> None:
    if session_id not in sessions:
        await websocket.close(code=4004)
        return
    await websocket.accept()
    session = sessions[session_id]
    session["ws"] = websocket

    # Replay any buffered logs that arrived before the WS connected.
    for frame in session["logs"]:
        try:
            await websocket.send_json(frame)
        except Exception:
            log.exception("replay send failed")
            return

    status = session.get("status")
    if status in ("completed", "failed"):
        try:
            await websocket.send_json({"type": "status", "status": status})
        except Exception:
            pass

    try:
        while True:
            # Keep the connection alive; client may send pings or be silent.
            await websocket.receive_text()
    except WebSocketDisconnect:
        session["ws"] = None

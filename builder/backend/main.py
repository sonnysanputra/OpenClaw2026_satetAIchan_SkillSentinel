"""FastAPI entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import deploy, files, skills, ssh, ws

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

app = FastAPI(title="OpenClaw Agent Builder API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ssh.router, prefix="/api", tags=["ssh"])
app.include_router(skills.router, prefix="/api", tags=["skills"])
app.include_router(deploy.router, prefix="/api", tags=["deploy"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(ws.router, tags=["ws"])


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

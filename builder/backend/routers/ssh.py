"""POST /api/ssh/test — non-destructive connectivity probe to the user's VPS."""
from __future__ import annotations

import asyncio
import io

import paramiko
from fastapi import APIRouter

from schemas.models import SshTestRequest, SshTestResponse
from services.ssh_deployment import _load_pkey

router = APIRouter()


@router.post("/ssh/test", response_model=SshTestResponse)
async def test_ssh(req: SshTestRequest) -> SshTestResponse:
    def _probe() -> SshTestResponse:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            if req.auth_method == "key":
                if not req.ssh_private_key:
                    return SshTestResponse(success=False, error="ssh_private_key is required")
                pkey = _load_pkey(req.ssh_private_key)
                client.connect(
                    req.host,
                    port=req.port,
                    username=req.user,
                    pkey=pkey,
                    timeout=10,
                    banner_timeout=10,
                    auth_timeout=10,
                )
            else:
                if not req.ssh_password:
                    return SshTestResponse(success=False, error="ssh_password is required")
                client.connect(
                    req.host,
                    port=req.port,
                    username=req.user,
                    password=req.ssh_password,
                    timeout=10,
                    banner_timeout=10,
                    auth_timeout=10,
                )

            _stdin, stdout, _stderr = client.exec_command(
                "lsb_release -d 2>/dev/null | cut -f2- || (uname -sr)"
            )
            os_info = stdout.read().decode(errors="replace").strip()

            _stdin, stdout, _stderr = client.exec_command("openclaw --version 2>/dev/null")
            stdout.read()
            installed = stdout.channel.recv_exit_status() == 0
            return SshTestResponse(success=True, os=os_info, openclaw_installed=installed)
        except Exception as e:
            return SshTestResponse(success=False, error=str(e))
        finally:
            try:
                client.close()
            except Exception:
                pass

    return await asyncio.get_event_loop().run_in_executor(None, _probe)

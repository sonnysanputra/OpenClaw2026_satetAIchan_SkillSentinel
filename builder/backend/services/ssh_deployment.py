"""SSH-based OpenClaw deployment to the user's VPS.

Paramiko is synchronous, so every blocking call is wrapped in
`loop.run_in_executor` to avoid stalling the FastAPI event loop.
"""
from __future__ import annotations

import asyncio
import io
import logging
import secrets
from typing import Awaitable, Callable

import paramiko

from schemas.models import DeployRequest
from services.file_generator import (
    generate_agents_md,
    generate_identity_md,
    generate_soul_md,
    generate_user_md,
)

log = logging.getLogger(__name__)

EmitFn = Callable[[str, str], Awaitable[None]]

COMMAND_TIMEOUT_S = 180


def _load_pkey(blob: str) -> paramiko.PKey:
    """Best-effort key loader. Try Ed25519, ECDSA, RSA in turn."""
    key_io = io.StringIO(blob)
    last_err: Exception | None = None
    for cls in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
        key_io.seek(0)
        try:
            return cls.from_private_key(key_io)
        except Exception as e:  # paramiko.SSHException + others
            last_err = e
            continue
    raise ValueError(f"Could not parse SSH private key: {last_err}")


def _shell_quote_single(s: str) -> str:
    """Quote arbitrary content for use inside single quotes in a shell command."""
    return s.replace("'", "'\\''")


class SshDeployer:
    """Run the full deployment sequence over a single SSH session."""

    def __init__(self, request: DeployRequest, emit: EmitFn):
        self.req = request
        self.emit = emit
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # -- connection ----------------------------------------------------------
    def _connect_sync(self) -> None:
        vps = self.req.vps
        if vps.auth_method == "key":
            if not vps.ssh_private_key:
                raise ValueError("ssh_private_key required when auth_method=key")
            pkey = _load_pkey(vps.ssh_private_key)
            self.client.connect(
                vps.host,
                port=vps.port,
                username=vps.user,
                pkey=pkey,
                timeout=15,
                banner_timeout=15,
                auth_timeout=15,
            )
        else:
            if not vps.ssh_password:
                raise ValueError("ssh_password required when auth_method=password")
            self.client.connect(
                vps.host,
                port=vps.port,
                username=vps.user,
                password=vps.ssh_password,
                timeout=15,
                banner_timeout=15,
                auth_timeout=15,
            )

    # -- exec ---------------------------------------------------------------
    async def _run(
        self,
        command: str,
        label: str,
        *,
        check: bool = True,
        echo_stdout: bool = True,
    ) -> tuple[int, str, str]:
        await self.emit("info", f"→ {label}")

        def _exec() -> tuple[int, str, str]:
            _stdin, stdout, stderr = self.client.exec_command(command, timeout=COMMAND_TIMEOUT_S)
            out = stdout.read().decode(errors="replace").strip()
            err = stderr.read().decode(errors="replace").strip()
            code = stdout.channel.recv_exit_status()
            return code, out, err

        loop = asyncio.get_event_loop()
        code, out, err = await loop.run_in_executor(None, _exec)

        if echo_stdout and out:
            # Stream long output line-by-line so the UI updates feel live.
            for line in out.splitlines()[:60]:
                await self.emit("info", line)

        if code != 0:
            if check:
                msg = err or out or f"exit code {code}"
                await self.emit("error", f"✗ {label}: {msg.splitlines()[0][:300] if msg else msg}")
            else:
                if err:
                    await self.emit("warning", f"⚠ {label}: {err.splitlines()[0][:200]}")
            return code, out, err

        await self.emit("success", f"✓ {label}")
        return code, out, err

    async def _write_file(self, remote_path: str, content: str, label: str) -> bool:
        delim = f"OPENCLAW_HEREDOC_{secrets.token_hex(6)}"
        quoted_path = f"'{_shell_quote_single(remote_path)}'"
        cmd = f"mkdir -p \"$(dirname {quoted_path})\" && cat > {quoted_path} << '{delim}'\n{content}\n{delim}\n"
        code, _, err = await self._run(cmd, label, echo_stdout=False)
        return code == 0

    # -- top-level ----------------------------------------------------------
    async def deploy(self) -> bool:
        req = self.req
        ident = req.identity
        await self.emit("info", f"Connecting to {req.vps.host}:{req.vps.port} as {req.vps.user}...")
        try:
            await asyncio.get_event_loop().run_in_executor(None, self._connect_sync)
        except Exception as e:
            await self.emit("error", f"SSH connection failed: {e}")
            return False
        await self.emit("success", "Connected to VPS")

        try:
            # Bootstrap: ensure Node 22 + OpenClaw installed.
            await self._ensure_node()
            code, _, _ = await self._run(
                "command -v openclaw >/dev/null && openclaw --version || echo MISSING",
                "Checking OpenClaw install",
                check=False,
            )
            if "MISSING" in (await self._capture("command -v openclaw || echo MISSING"))[0]:
                if not (await self._run("npm install -g openclaw", "Installing OpenClaw via npm"))[0] == 0:
                    return False

            await self._run("openclaw setup --non-interactive || true", "openclaw setup", check=False)
            workspace = ident.workspace_path
            if not (await self._run(f"mkdir -p '{_shell_quote_single(workspace)}'", "Creating workspace dir"))[0] == 0:
                return False

            # Generate + upload workspace files.
            files = {
                f"{workspace}/SOUL.md": generate_soul_md(ident, req.persona),
                f"{workspace}/USER.md": generate_user_md(req.user_context),
                f"{workspace}/AGENTS.md": generate_agents_md(req.instructions),
                f"{workspace}/IDENTITY.md": generate_identity_md(ident),
            }
            for path, body in files.items():
                if not await self._write_file(path, body, f"Writing {path.rsplit('/', 1)[-1]}"):
                    return False

            # Register agent.
            reg = (
                f"openclaw agents add {ident.agent_id} "
                f"--workspace '{_shell_quote_single(workspace)}' --non-interactive"
            )
            if not (await self._run(reg, f"Registering agent: {ident.agent_id}"))[0] == 0:
                return False

            # Configure model.
            model_str = f"{req.model.provider}/{req.model.model}"
            await self._run(
                f"openclaw config set agents.defaults.model {model_str}",
                f"Setting default model: {model_str}",
                check=False,
            )
            if req.model.heartbeat_model:
                await self._run(
                    f"openclaw config set agents.defaults.heartbeatModel {req.model.heartbeat_model}",
                    f"Setting heartbeat model: {req.model.heartbeat_model}",
                    check=False,
                )

            # Install skills (only approved/overridden made it this far).
            for skill in req.skills:
                if skill.security_status == "overridden":
                    reason = skill.security_reason or "no reason recorded"
                    await self.emit("warning", f"⚠ Installing OVERRIDDEN skill {skill.name}: {reason}")
                await self._run(
                    f"openclaw skills install {skill.id}",
                    f"Installing skill: {skill.name}",
                    check=False,
                )

            # Bind channels.
            for channel in req.channels.selected:
                acct = req.channels.account_ids.get(channel, "").strip()
                binding = f"{channel}:{acct}" if acct else channel
                await self._run(
                    f"openclaw agents bind --agent {ident.agent_id} --bind {binding}",
                    f"Binding channel: {binding}",
                    check=False,
                )

            # Start daemon under pm2.
            await self._run("npm install -g pm2", "Installing pm2", check=False)
            await self._run("pm2 start openclaw -- daemon start", "Starting OpenClaw daemon under pm2", check=False)
            await self._run("pm2 save", "Saving pm2 process list", check=False)
            await self._run("openclaw doctor || true", "Running openclaw doctor", check=False)

            await self.emit("success", f"Deployment complete — agent '{ident.agent_id}' is live")
            return True
        finally:
            try:
                self.client.close()
            except Exception:
                pass

    # -- helpers ------------------------------------------------------------
    async def _ensure_node(self) -> None:
        code, out, _ = await self._run("node --version || true", "Checking Node.js version", check=False, echo_stdout=False)
        version_str = out.strip().lstrip("v")
        major = 0
        if version_str:
            try:
                major = int(version_str.split(".")[0])
            except ValueError:
                major = 0
        if major >= 22:
            await self.emit("success", f"✓ Node.js {out.strip()} present")
            return
        await self.emit("info", "Node 22+ not found — installing via nodesource")
        
        sudo_prefix = "sudo "
        vps = self.req.vps
        if vps.user != "root" and vps.auth_method == "password" and vps.ssh_password:
            # Provide password to sudo over stdin to prevent hanging
            sudo_prefix = f"echo '{_shell_quote_single(vps.ssh_password)}' | sudo -S "

        install = (
            f"curl -fsSL https://deb.nodesource.com/setup_22.x | {sudo_prefix}-E bash - && "
            f"{sudo_prefix}apt-get install -y nodejs"
        )
        await self._run(install, "Installing Node.js 22", check=False)

    async def _capture(self, command: str) -> tuple[str, str]:
        def _exec() -> tuple[str, str]:
            _stdin, stdout, stderr = self.client.exec_command(command, timeout=30)
            return stdout.read().decode().strip(), stderr.read().decode().strip()

        return await asyncio.get_event_loop().run_in_executor(None, _exec)

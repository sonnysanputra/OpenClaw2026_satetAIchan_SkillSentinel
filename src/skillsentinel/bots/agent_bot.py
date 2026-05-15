"""Generic SkillSentinel agent bot.

Each bot is a Discord channel listener tied to one OpenClaw agent.
On @-mention, the bot invokes its OpenClaw agent with a STRICT prompt that
forces use of only its own skill. If OpenClaw returns empty (rate limit /
Claude decides not to elaborate), the bot falls back to running the skill
directly and formatting the JSON output.

Strict sequential cascade: each agent posts its own findings, mentions the
next agent, and waits. No agent does another agent's job.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import discord

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

PIPELINE: tuple[str, ...] = (
    "coordinator", "intake", "static", "semantic", "dynamic", "verdict",
)

AGENT_EMOJI: dict[str, str] = {
    "coordinator": "🎯", "intake": "🛡️", "static": "📦",
    "semantic": "🧠", "dynamic": "🧪", "verdict": "⚖️",
}

VERDICT_COLORS: dict[str, int] = {
    "ALLOW": 0x16A34A, "WARN": 0xCA8A04, "REVIEW": 0xC026D3,
    "BLOCK": 0xDC2626, "INFO": 0x3B82F6,
}

# Map agent role -> wrapper script path (for fallback direct invocation).
WRAPPERS: dict[str, str] = {
    "intake":   "/usr/lib/node_modules/openclaw/skills/skillsentinel-intake/intake.py",
    "static":   "/usr/lib/node_modules/openclaw/skills/skillsentinel-static/static.py",
    "semantic": "/usr/lib/node_modules/openclaw/skills/skillsentinel-semantic/semantic.py",
    "dynamic":  "/usr/lib/node_modules/openclaw/skills/skillsentinel-dynamic/dynamic.py",
    "verdict":  "/usr/lib/node_modules/openclaw/skills/skillsentinel-verdict/verdict.py",
}

# Friendly one-line descriptions of each agent's job (used in fallback summaries).
AGENT_DESCRIPTIONS: dict[str, str] = {
    "intake":   "structural and manifest analysis",
    "static":   "AST + regex code analysis",
    "semantic": "LLM-based intent comparison",
    "dynamic":  "sandboxed execution with honeypot credentials",
    "verdict":  "final adjudication via deterministic scoring",
}

BOT_IDS_FILE = Path("/root/.skillsentinel/bot_ids.json")
OPENCLAW_TIMEOUT_SECS = 90


def load_bot_ids() -> dict[str, int]:
    try:
        return json.loads(BOT_IDS_FILE.read_text())
    except FileNotFoundError:
        return {}


def save_bot_id(agent: str, bot_id: int) -> None:
    BOT_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ids = load_bot_ids()
    ids[agent] = bot_id
    BOT_IDS_FILE.write_text(json.dumps(ids, indent=2))


def next_agent(current: str) -> Optional[str]:
    try:
        idx = PIPELINE.index(current)
    except ValueError:
        return None
    return PIPELINE[idx + 1] if idx + 1 < len(PIPELINE) else None


def extract_bundle_path(text: str) -> Optional[str]:
    m = re.search(r'/opt/skillsentinel/corpus/\S+', text)
    if m:
        return m.group(0).rstrip('.,;!?` ')
    m = re.search(r'corpus/[A-Za-z0-9/_.-]+', text)
    if m:
        return f"/opt/skillsentinel/{m.group(0).rstrip('.,;!?` ')}"
    return None


def _strict_prompt(agent: str, bundle_path: str) -> str:
    """Constrain Claude to ONLY use the named skill, return ONLY a brief summary."""
    desc = AGENT_DESCRIPTIONS.get(agent, "security analysis")
    return (
        f"Run the `skillsentinel-{agent}` skill on the path `{bundle_path}` "
        f"to perform {desc}.\n\n"
        f"STRICT RULES:\n"
        f"- Use ONLY the `skillsentinel-{agent}` skill. Do NOT use any other skill.\n"
        f"- Do NOT read files directly. Do NOT analyze files yourself.\n"
        f"- After the skill returns, summarize ONLY ITS findings in 1-2 short sentences.\n"
        f"- Do NOT speculate about what other agents in the pipeline might find.\n"
        f"- End your response with EXACTLY one line: VERDICT: <ALLOW|WARN|REVIEW|BLOCK>"
    )


def _extract_verdict(text: str) -> str:
    m = re.search(r"VERDICT\s*:\s*(ALLOW|WARN|REVIEW|BLOCK)", text, re.I)
    if m:
        return m.group(1).upper()
    for word in ("BLOCK", "REVIEW", "WARN", "ALLOW"):
        if word in text.upper().split()[-15:]:
            return word
    return "INFO"


def _extract_assistant_text(openclaw_json: dict) -> str:
    for key_path in (
        ("finalAssistantVisibleText",),
        ("result", "finalAssistantVisibleText"),
        ("finalAssistantRawText",),
        ("result", "finalAssistantRawText"),
    ):
        cur = openclaw_json
        try:
            for k in key_path:
                cur = cur[k]
            if isinstance(cur, str) and cur.strip():
                return cur
        except (KeyError, TypeError):
            continue
    return ""


async def invoke_openclaw_agent(agent: str, bundle_path: str) -> tuple[str, str]:
    """Try OpenClaw agent first; returns (summary_text, verdict)."""
    prompt = _strict_prompt(agent, bundle_path)
    cmd = [
        "openclaw", "agent", "--local",
        "--agent", agent, "--json",
        "--thinking", "low",  # minimize tokens & latency
        "--message", prompt,
    ]
    log.info("openclaw.invoke agent=%s", agent)
    try:
        proc = await asyncio.to_thread(
            subprocess.run, cmd,
            capture_output=True, text=True, timeout=OPENCLAW_TIMEOUT_SECS,
            env={**os.environ, "SKILLSENTINEL_QUIET": "1"},
        )
    except subprocess.TimeoutExpired:
        return "", "INFO"
    if proc.returncode != 0:
        return "", "INFO"
    stdout = proc.stdout
    brace = stdout.find("{")
    if brace < 0:
        return "", "INFO"
    try:
        data = json.loads(stdout[brace:])
    except json.JSONDecodeError:
        return "", "INFO"
    text = _extract_assistant_text(data)
    return text, _extract_verdict(text) if text else "INFO"


async def invoke_skill_directly(agent: str, bundle_path: str) -> dict:
    """Fallback: run the skill wrapper directly and parse its JSON output."""
    wrapper = WRAPPERS.get(agent)
    if not wrapper:
        return {"agent": agent, "verdict_hint": "INFO", "n_findings": 0,
                "findings": [], "error": "no wrapper registered"}
    proc = await asyncio.to_thread(
        subprocess.run, [wrapper, bundle_path],
        capture_output=True, text=True, timeout=90,
        env={**os.environ, "SKILLSENTINEL_QUIET": "1"},
    )
    if proc.returncode != 0:
        return {"agent": agent, "verdict_hint": "INFO", "n_findings": 0,
                "findings": [], "error": (proc.stderr or "exit nonzero")[:500]}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"agent": agent, "verdict_hint": "INFO", "n_findings": 0,
                "findings": [], "error": f"JSON parse: {e}"}


def _format_skill_summary(skill_result: dict, agent: str) -> str:
    """Format the skill's JSON output into a human-friendly 1-2 sentence summary."""
    n = skill_result.get("n_findings", 0)
    verdict = skill_result.get("verdict_hint", "INFO")
    findings = skill_result.get("findings") or []
    if not findings:
        return f"No findings from {agent} agent. VERDICT: {verdict}"
    worst = findings[0]
    msg = (
        f"{n} finding(s). Headline: **[{worst.get('severity', '?')}] "
        f"{worst.get('category', '?')}** — {worst.get('message', '')[:200]}\n\n"
        f"VERDICT: {verdict}"
    )
    return msg


class AgentBot(discord.Client):
    def __init__(self, *, agent: str, channel_id: int, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, **kwargs)
        self.agent = agent
        self.channel_id = channel_id

    async def on_ready(self) -> None:
        log.info("%s online as %s (id=%s)", self.agent, self.user, self.user.id)
        save_bot_id(self.agent, self.user.id)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.id == self.user.id:
            return
        if message.channel.id != self.channel_id:
            return
        if self.user not in message.mentions:
            return
        bundle_path = extract_bundle_path(message.content)
        if self.agent == "coordinator":
            await self._handle_coordinator(message, bundle_path)
        else:
            await self._handle_specialist(message, bundle_path)

    async def _handle_coordinator(self, message, bundle_path):
        if not bundle_path:
            await message.channel.send(
                "🎯 I need a bundle path. Try: "
                "`@SkillSentinel-Coordinator scan corpus/malicious/03-typosquat-dependency`"
            )
            return
        embed = discord.Embed(
            title="🎯 New scan request",
            description=f"Routing `{Path(bundle_path).name}` through the 5-agent OpenClaw pipeline.",
            color=VERDICT_COLORS["INFO"],
        )
        embed.set_footer(text="agent: coordinator")
        await message.channel.send(embed=embed)
        await self._handoff(message.channel, "intake", bundle_path)

    async def _handle_specialist(self, message, bundle_path):
        if not bundle_path:
            await message.channel.send(
                f"{AGENT_EMOJI[self.agent]} I need a bundle path in the message."
            )
            return

        try:
            await message.add_reaction(AGENT_EMOJI[self.agent])
        except discord.HTTPException:
            pass

        thinking = await message.channel.send(
            f"{AGENT_EMOJI[self.agent]} **{self.agent.title()}**: invoking OpenClaw + Claude on `{Path(bundle_path).name}`..."
        )

        # 1. Always run the skill directly (cheap, deterministic, always works).
        skill_result = await invoke_skill_directly(self.agent, bundle_path)
        skill_verdict = skill_result.get("verdict_hint", "INFO")

        # 2. Try OpenClaw + Claude for natural-language summary (best effort).
        nl_summary, nl_verdict = await invoke_openclaw_agent(self.agent, bundle_path)

        # 3. Pick the better verdict (prefer OpenClaw's if non-empty; else skill's).
        verdict = nl_verdict if nl_summary.strip() else skill_verdict
        summary = nl_summary.strip() or _format_skill_summary(skill_result, self.agent)

        try:
            await thinking.delete()
        except discord.HTTPException:
            pass

        color = VERDICT_COLORS.get(verdict, VERDICT_COLORS["INFO"])
        embed = discord.Embed(
            title=f"{AGENT_EMOJI[self.agent]} {self.agent.title()} agent — {verdict}",
            description=summary[:1800],
            color=color,
        )
        if skill_result.get("error"):
            embed.add_field(name="skill error", value=str(skill_result["error"])[:500], inline=False)
        embed.add_field(
            name="findings",
            value=str(skill_result.get("n_findings", 0)),
            inline=True,
        )
        embed.add_field(
            name="source",
            value="OpenClaw + claude-sonnet-4-6" if nl_summary.strip() else "skill direct (Claude empty)",
            inline=True,
        )
        embed.set_footer(text=f"agent: {self.agent}")
        await message.channel.send(embed=embed)

        nxt = next_agent(self.agent)
        if nxt:
            await self._handoff(message.channel, nxt, bundle_path)
        else:
            await message.channel.send(
                f"✅ Pipeline complete. Final verdict: **{verdict}**."
            )

    async def _handoff(self, channel, next_name, bundle_path):
        ids = load_bot_ids()
        target_id = ids.get(next_name)
        if not target_id:
            await channel.send(
                f"⚠️ Can't hand off to **{next_name}** — bot not connected yet."
            )
            return
        await channel.send(
            f"<@{target_id}> your turn — scan {bundle_path}"
        )


def main() -> int:
    agent = os.environ.get("AGENT_NAME", "").lower()
    if agent not in PIPELINE:
        print(f"AGENT_NAME must be one of {PIPELINE}, got: {agent!r}", file=sys.stderr)
        return 2
    token = os.environ.get(f"SKILLSENTINEL_BOT_TOKEN_{agent.upper()}")
    if not token:
        print(f"Missing SKILLSENTINEL_BOT_TOKEN_{agent.upper()}", file=sys.stderr)
        return 2
    channel_str = os.environ.get("SKILLSENTINEL_DISCORD_CHANNEL_ID")
    if not channel_str:
        print("Missing SKILLSENTINEL_DISCORD_CHANNEL_ID", file=sys.stderr)
        return 2
    bot = AgentBot(agent=agent, channel_id=int(channel_str))
    bot.run(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())

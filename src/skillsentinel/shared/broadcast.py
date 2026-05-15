"""Discord broadcast utility for SkillSentinel agents.

Posts color-coded embeds to a Discord channel via webhook. Reads the webhook URL
from the ``SKILLSENTINEL_DISCORD_WEBHOOK`` environment variable. Designed to fail
silently — if Discord is unreachable or the webhook is unset, the calling agent
keeps working and the scan still completes.

Why a webhook (not a bot account):

* No bot token to leak or rotate — webhook URLs are scoped to one channel.
* Stateless: works from any process, container, or short-lived skill.
* Zero extra dependencies — stdlib only.

Usage from any agent:

    from skillsentinel.shared.broadcast import broadcast
    broadcast(
        agent="intake",
        level="ALLOW",
        message="Bundle hello-skill passed structural checks",
        fields={"bundle_sha": "abc123…", "findings": 0},
    )

CLI smoke test:

    python -m skillsentinel.shared.broadcast intake WARN "Test message"
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

# Discord embed colors expressed as decimal RGB integers.
_COLORS: dict[str, int] = {
    "ALLOW": 0x16A34A,   # green-600  — bundle is safe
    "WARN": 0xCA8A04,    # yellow-600 — minor issue, ship with caveat
    "REVIEW": 0xC026D3,  # fuchsia-600 — needs a human
    "BLOCK": 0xDC2626,   # red-600    — do not install
    "INFO": 0x3B82F6,    # blue-500   — neutral status update
}

_LEVEL_EMOJI: dict[str, str] = {
    "ALLOW": "✅",
    "WARN": "⚠️",
    "REVIEW": "🔍",
    "BLOCK": "🚫",
    "INFO": "🛡️",
}

WEBHOOK_ENV = "SKILLSENTINEL_DISCORD_WEBHOOK"
DEFAULT_USERNAME = "SkillSentinel"
TIMEOUT_SECONDS = 5
MAX_FIELD_VALUE_LEN = 1024  # Discord's per-field cap.


def broadcast(
    agent: str,
    level: str,
    message: str,
    fields: dict[str, Any] | None = None,
    *,
    username: str = DEFAULT_USERNAME,
) -> bool:
    """Post a color-coded embed to Discord.

    Args:
        agent: Name of the emitting agent ("intake", "static", …). Appears in footer.
        level: One of ALLOW / WARN / REVIEW / BLOCK / INFO (case-insensitive).
        message: Main embed description — keep it human and skimmable.
        fields: Optional structured key/value pairs rendered inline on the embed.
        username: Override the webhook's display name for this post.

    Returns:
        True on a 2xx response from Discord, False on any error.

    Never raises — broadcast failures should never break a scan pipeline.
    """
    url = os.environ.get(WEBHOOK_ENV)
    if not url:
        log.warning("broadcast.no_webhook_configured: %s unset", WEBHOOK_ENV)
        return False

    level_upper = level.upper()
    color = _COLORS.get(level_upper, _COLORS["INFO"])
    emoji = _LEVEL_EMOJI.get(level_upper, _LEVEL_EMOJI["INFO"])

    embed: dict[str, Any] = {
        "title": f"{emoji} {level_upper}",
        "description": message,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": f"agent: {agent}"},
    }

    if fields:
        embed["fields"] = [
            {
                "name": str(k)[:256],
                "value": str(v)[:MAX_FIELD_VALUE_LEN] or "—",
                "inline": True,
            }
            for k, v in fields.items()
        ]

    payload = {"username": username, "embeds": [embed]}

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "SkillSentinel/0.1 (+https://github.com/sonnysanputra/skillsentinel)"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            if 200 <= resp.status < 300:
                return True
            log.warning("broadcast.bad_status: %s", resp.status)
            return False
    except urllib.error.URLError as exc:
        log.warning("broadcast.network_error: %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001 — never crash the agent
        log.warning("broadcast.unexpected_error: %s", exc)
        return False


def _main() -> int:
    if len(sys.argv) < 4:
        print(
            "Usage: python -m skillsentinel.shared.broadcast <agent> <level> <message>",
            file=sys.stderr,
        )
        return 2
    ok = broadcast(agent=sys.argv[1], level=sys.argv[2], message=sys.argv[3])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_main())

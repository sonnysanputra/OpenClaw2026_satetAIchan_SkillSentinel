"""Discord broadcast utility for SkillSentinel agents.

Posts color-coded embeds via webhook (env var SKILLSENTINEL_DISCORD_WEBHOOK).
Stdlib only, fails silently. Set SKILLSENTINEL_QUIET=1 to suppress entirely
(used when a wrapper is invoked from a bot to avoid duplicate messages).
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

_COLORS: dict[str, int] = {
    "ALLOW": 0x16A34A, "WARN": 0xCA8A04, "REVIEW": 0xC026D3,
    "BLOCK": 0xDC2626, "INFO": 0x3B82F6,
}

_LEVEL_EMOJI: dict[str, str] = {
    "ALLOW": "✅", "WARN": "⚠️", "REVIEW": "🔍",
    "BLOCK": "🚫", "INFO": "🛡️",
}

WEBHOOK_ENV = "SKILLSENTINEL_DISCORD_WEBHOOK"
DEFAULT_USERNAME = "SkillSentinel"
TIMEOUT_SECONDS = 5
MAX_FIELD_VALUE_LEN = 1024


def broadcast(
    agent: str,
    level: str,
    message: str,
    fields: dict[str, Any] | None = None,
    *,
    username: str = DEFAULT_USERNAME,
) -> bool:
    """Post a color-coded embed to Discord. Never raises."""
    # Suppress when invoked from a bot wrapper (avoids duplicate messages).
    if os.environ.get("SKILLSENTINEL_QUIET") == "1":
        return False

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
            {"name": str(k)[:256], "value": str(v)[:MAX_FIELD_VALUE_LEN] or "—", "inline": True}
            for k, v in fields.items()
        ]

    payload = {"username": username, "embeds": [embed]}

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SkillSentinel/0.1 (+https://github.com/sonnysanputra/skillsentinel)",
            },
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
    except Exception as exc:
        log.warning("broadcast.unexpected_error: %s", exc)
        return False


def _main() -> int:
    if len(sys.argv) < 4:
        print("Usage: python -m skillsentinel.shared.broadcast <agent> <level> <message>",
              file=sys.stderr)
        return 2
    ok = broadcast(agent=sys.argv[1], level=sys.argv[2], message=sys.argv[3])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_main())

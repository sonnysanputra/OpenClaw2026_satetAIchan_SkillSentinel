"""In-memory deployment session registry. Ephemeral by design — wiped on restart."""
from __future__ import annotations

from typing import Any

# session_id -> { request, logs[], status, ws }
sessions: dict[str, dict[str, Any]] = {}

"""SkillsHub catalogue — parsed from the awesome-openclaw-agents README.

Cached in-memory for `skillshub_cache_ttl` seconds. If the README cannot be
fetched or parsed (network down, format change), we fall back to a small
hard-coded demo list so the UI is never empty.
"""
from __future__ import annotations

import logging
import re
import time
from urllib.parse import urlparse

import httpx

from core.config import settings

log = logging.getLogger(__name__)

_cache: dict[str, object] = {"data": None, "fetched_at": 0.0}


_DEMO_SKILLS: list[dict] = [
    {
        "id": "github-integration",
        "name": "GitHub Integration",
        "description": "Manage issues, PRs, and repos from your agent.",
        "author": "openclaw-team",
        "category": "productivity",
        "install_count": 4821,
        "raw_url": "https://raw.githubusercontent.com/openclaw/skill-github/main/SKILL.md",
    },
    {
        "id": "weather",
        "name": "Weather",
        "description": "Lookup forecasts via open-meteo. No API key required.",
        "author": "community",
        "category": "utility",
        "install_count": 1200,
        "raw_url": "https://raw.githubusercontent.com/openclaw/skill-weather/main/SKILL.md",
    },
    {
        "id": "calendar",
        "name": "Calendar",
        "description": "Read and schedule events on Google/Apple/CalDAV calendars.",
        "author": "community",
        "category": "productivity",
        "install_count": 980,
        "raw_url": "https://raw.githubusercontent.com/openclaw/skill-calendar/main/SKILL.md",
    },
    {
        "id": "websearch",
        "name": "Web Search",
        "description": "DuckDuckGo / SerpAPI web search wrapper.",
        "author": "community",
        "category": "research",
        "install_count": 3100,
        "raw_url": "https://raw.githubusercontent.com/openclaw/skill-websearch/main/SKILL.md",
    },
    {
        "id": "memory-vault",
        "name": "Memory Vault",
        "description": "Long-term semantic memory backed by SQLite + vectors.",
        "author": "community",
        "category": "memory",
        "install_count": 540,
        "raw_url": "https://raw.githubusercontent.com/openclaw/skill-memory-vault/main/SKILL.md",
    },
    {
        "id": "image-gen",
        "name": "Image Gen",
        "description": "Generate images via FLUX / SDXL endpoints.",
        "author": "community",
        "category": "media",
        "install_count": 660,
        "raw_url": "https://raw.githubusercontent.com/openclaw/skill-image-gen/main/SKILL.md",
    },
    # A deliberately suspicious one so the security gate has something to flag in demos.
    {
        "id": "system-cleaner",
        "name": "System Cleaner",
        "description": "Runs rm -rf and curl|sh to 'optimize' the host. Demo of a hostile skill.",
        "author": "untrusted",
        "category": "system",
        "install_count": 3,
        "raw_url": "https://raw.githubusercontent.com/example/skill-system-cleaner/main/SKILL.md",
    },
]


async def fetch_skills(search: str = "") -> list[dict]:
    now = time.time()
    fetched_at = float(_cache.get("fetched_at") or 0.0)
    data = _cache.get("data")
    if data is None or (now - fetched_at) > settings.skillshub_cache_ttl:
        data = await _fetch_remote()
        _cache["data"] = data
        _cache["fetched_at"] = now

    skills: list[dict] = list(data or [])
    if search:
        needle = search.lower().strip()
        skills = [
            s
            for s in skills
            if needle in s["name"].lower()
            or needle in s["description"].lower()
            or needle in s["author"].lower()
        ]
    return skills


async def _fetch_remote() -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            resp = await c.get(settings.skillshub_readme_url)
            resp.raise_for_status()
        parsed = _parse_skills(resp.text)
        if parsed and len(parsed) > 5:
            return parsed
        log.warning("SkillsHub README parsed too few skills; using demo skills")
    except Exception as e:
        log.warning("SkillsHub fetch failed (%s); using demo skills", e)
    return list(_DEMO_SKILLS)


_LINK_RE = re.compile(
    r"\[(?P<name>[^\]]+)\]\((?P<url>https://github\.com/[^\)]+)\)[^\n]*?[—–-]\s*(?P<desc>[^\n]+)"
)


def _parse_skills(readme: str) -> list[dict]:
    skills: list[dict] = []
    seen: set[str] = set()
    for i, m in enumerate(_LINK_RE.finditer(readme)):
        url = m.group("url").rstrip(".,)")
        if url in seen:
            continue
        seen.add(url)
        path = urlparse(url).path.strip("/")
        parts = path.split("/")
        author = parts[0] if parts else "unknown"
        repo = parts[1] if len(parts) > 1 else "skill"
        # Construct a best-effort raw URL to SKILL.md on the default branch.
        raw_url = f"https://raw.githubusercontent.com/{author}/{repo}/main/SKILL.md"
        skills.append(
            {
                "id": f"{author}-{repo}".lower(),
                "name": m.group("name").strip(),
                "description": m.group("desc").strip(),
                "author": author,
                "category": "community",
                "install_count": 0,
                "raw_url": raw_url,
            }
        )
        if i > 200:
            break
    return skills

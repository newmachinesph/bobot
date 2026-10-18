"""Fetch and cache platform Markdown docs (skill.md, heartbeat.md, messaging.md).

Files are fetched from the platform URL once per day.  If a fetch fails
the loader falls back to the most recent cached version so the bot can
still operate offline.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# How long before we re-fetch (seconds).  Default: 24 hours.
_CACHE_TTL = 86_400

_DOC_NAMES = ("skill.md", "heartbeat.md", "messaging.md")


def _cache_dir(data_dir: Path) -> Path:
    d = data_dir / "docs_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_path(data_dir: Path, name: str) -> Path:
    return _cache_dir(data_dir) / name


def _is_stale(path: Path) -> bool:
    if not path.exists():
        return True
    age = time.time() - path.stat().st_mtime
    return age > _CACHE_TTL


async def _fetch_doc(client: httpx.AsyncClient, url: str) -> str | None:
    """Attempt to GET a single document.  Returns None on failure."""
    try:
        resp = await client.get(url, timeout=15.0)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


async def load_skills(
    platform_url: str,
    data_dir: Path,
    api_key: str = "",
    docs_url: str = "",
) -> tuple[str, str, str]:
    """Return ``(skills_md, heartbeat_md, messaging_md)``.

    Fetches from the platform if the cache is stale; otherwise reads
    from disk.  If both fetch and cache miss, returns empty strings.

    Parameters
    ----------
    platform_url:
        Base URL of the bobot.ph API (e.g. ``http://localhost:8000/v1``).
    data_dir:
        Path where cached files are stored.
    api_key:
        Optional bearer token sent with the request.
    docs_url:
        Base URL for skill/heartbeat/messaging docs. If empty, falls back to
        ``platform_url`` with ``/docs/`` appended. For bobot.ph the docs are
        served from the frontend (e.g. ``http://localhost:3000``).
    """
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Resolve where docs live: explicit docs_url wins, otherwise guess from API URL.
    if docs_url:
        base_docs = docs_url.rstrip("/")
    else:
        # Strip /v1 suffix and assume docs are at /docs on the same host.
        base_docs = platform_url.rstrip("/").removesuffix("/v1") + "/docs"

    results: list[str] = []

    async with httpx.AsyncClient(headers=headers) as client:
        for name in _DOC_NAMES:
            cached = _cache_path(data_dir, name)

            if not _is_stale(cached):
                logger.debug("Using cached %s", name)
                results.append(cached.read_text(encoding="utf-8"))
                continue

            # Attempt fresh fetch.
            url = f"{base_docs}/{name}"
            content = await _fetch_doc(client, url)

            if content is not None:
                cached.write_text(content, encoding="utf-8")
                logger.info("Fetched and cached %s", name)
                results.append(content)
            elif cached.exists():
                logger.warning("Fetch failed for %s — falling back to cache", name)
                results.append(cached.read_text(encoding="utf-8"))
            else:
                logger.warning("No cache for %s and fetch failed — using empty string", name)
                results.append("")

    skills_md, heartbeat_md, messaging_md = results
    return skills_md, heartbeat_md, messaging_md

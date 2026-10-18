"""Shared httpx client helper for bobot.ph API tools.

Provides a pre-configured async HTTP client with authentication,
base URL, and sensible timeouts.
"""

from __future__ import annotations

import os

import httpx


def get_client() -> httpx.AsyncClient:
    """Create a configured httpx.AsyncClient for the bobot.ph API.

    Reads configuration from environment variables:
        BOBOT_API_KEY: API key for bot authentication (required).
        BOBOT_PLATFORM_URL: Base URL for the API (default: http://localhost:8000/v1).

    Returns:
        An httpx.AsyncClient with base_url, authorization header, and timeout set.

    Raises:
        RuntimeError: If BOBOT_API_KEY is not set.
    """
    api_key = os.environ.get("BOBOT_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "BOBOT_API_KEY environment variable is not set. "
            "Cannot authenticate with the bobot.ph API."
        )

    base_url = os.environ.get("BOBOT_PLATFORM_URL", "http://localhost:8000/v1")

    return httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(15.0),
    )

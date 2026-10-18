"""Heartbeat tool for the bobot.ph platform.

Sends periodic heartbeats so the platform knows the bot is alive
and returns trust/jail/rate-limit status.
"""

from __future__ import annotations

import os

import httpx
from agents import function_tool

from src.tools.client import get_client


@function_tool
async def send_heartbeat() -> str:
    """Send a heartbeat to bobot.ph to confirm this bot is active.

    Returns:
        A formatted string with trust_score, jail_status,
        rate_limit_remaining, and strikes from the platform response.
    """
    bot_id = os.environ.get("BOBOT_BOT_ID", "")
    if not bot_id:
        return "Error: BOBOT_BOT_ID is not set. Cannot send heartbeat."

    try:
        async with get_client() as client:
            resp = await client.post(
                "/bots/heartbeat",
                json={"bot_id": bot_id, "status": "active"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Heartbeat failed (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Heartbeat failed (network error): {exc}"
    except RuntimeError as exc:
        return f"Heartbeat failed: {exc}"

    trust_score = data.get("trust_score", "unknown")
    jail_status = data.get("jail_status", "unknown")
    rate_remaining = data.get("rate_limit_remaining", "unknown")
    strikes = data.get("strikes", "unknown")

    return (
        f"Heartbeat sent successfully.\n"
        f"  Trust score: {trust_score}\n"
        f"  Jail status: {jail_status}\n"
        f"  Rate limit remaining: {rate_remaining}\n"
        f"  Strikes: {strikes}"
    )

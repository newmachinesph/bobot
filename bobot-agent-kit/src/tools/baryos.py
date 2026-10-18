"""Baryo discovery tools for the bobot.ph platform.

Allows the bot to explore and learn about baryos (communities).
"""

from __future__ import annotations

import httpx
from agents import function_tool

from src.tools.client import get_client


@function_tool
async def list_baryos() -> str:
    """List all public baryos on bobot.ph.

    Returns:
        A formatted list of baryos with names, descriptions, and member counts.
    """
    try:
        async with get_client() as client:
            resp = await client.get("/baryos/")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to list baryos (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to list baryos (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to list baryos: {exc}"

    baryos = data if isinstance(data, list) else data.get("baryos", [])

    if not baryos:
        return "No public baryos found."

    lines = [f"Public baryos ({len(baryos)}):"]
    for b in baryos:
        name = b.get("name", "?")
        description = b.get("description", "")
        members = b.get("member_count", 0)
        post_count = b.get("post_count", 0)

        lines.append(f"  /{name} ({members} members, {post_count} posts)")
        if description:
            # Truncate long descriptions
            desc = description if len(description) <= 100 else description[:97] + "..."
            lines.append(f"    {desc}")

    return "\n".join(lines)


@function_tool
async def get_baryo(name: str) -> str:
    """Get details about a specific baryo on bobot.ph.

    Args:
        name: The baryo name to look up (e.g. "weather", "news").

    Returns:
        Detailed information about the baryo including rules, description,
        and activity stats.
    """
    try:
        async with get_client() as client:
            resp = await client.get(f"/baryos/{name}")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return f"Baryo /{name} not found."
        return f"Failed to get baryo (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to get baryo (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to get baryo: {exc}"

    baryo_name = data.get("name", name)
    description = data.get("description", "No description.")
    members = data.get("member_count", 0)
    post_count = data.get("post_count", 0)
    rules = data.get("rules", [])
    created = data.get("created_at", "")

    lines = [
        f"/{baryo_name}",
        f"  {description}",
        f"  Members: {members}  |  Posts: {post_count}",
    ]
    if created:
        lines.append(f"  Created: {created}")
    if rules:
        lines.append("  Rules:")
        for i, rule in enumerate(rules, 1):
            rule_text = rule if isinstance(rule, str) else rule.get("text", str(rule))
            lines.append(f"    {i}. {rule_text}")

    return "\n".join(lines)

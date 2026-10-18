"""Reply tools for the bobot.ph platform.

Allows the bot to reply to posts and to other replies (nested threads).
"""

from __future__ import annotations

import httpx
from agents import function_tool

from src.tools.client import get_client


@function_tool
async def reply_to_post(post_id: str, content: str, source_url: str) -> str:
    """Reply to a post on bobot.ph.

    Every reply from a bot MUST include a source_url.

    Args:
        post_id: The UUID of the post to reply to.
        content: The reply content text.
        source_url: URL backing the claims in the reply. REQUIRED for bots.

    Returns:
        A success message with the reply ID, or an error description.
    """
    if not source_url:
        return "Error: source_url is REQUIRED for bot replies."

    try:
        async with get_client() as client:
            resp = await client.post(
                f"/posts/{post_id}/replies",
                json={"content": content, "source_url": source_url},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to reply (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to reply (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to reply: {exc}"

    reply_id = data.get("id", "unknown")
    return f"Reply posted successfully.\n  Reply ID: {reply_id}\n  On post: {post_id}"


@function_tool
async def reply_to_reply(
    post_id: str, parent_id: str, content: str, source_url: str
) -> str:
    """Reply to a specific reply in a nested thread on bobot.ph.

    Every reply from a bot MUST include a source_url.

    Args:
        post_id: The UUID of the root post.
        parent_id: The UUID of the reply being responded to.
        content: The reply content text.
        source_url: URL backing the claims in the reply. REQUIRED for bots.

    Returns:
        A success message with the reply ID, or an error description.
    """
    if not source_url:
        return "Error: source_url is REQUIRED for bot replies."

    try:
        async with get_client() as client:
            resp = await client.post(
                f"/posts/{post_id}/replies",
                params={"parent_id": parent_id},
                json={"content": content, "source_url": source_url},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to reply (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to reply (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to reply: {exc}"

    reply_id = data.get("id", "unknown")
    return (
        f"Nested reply posted successfully.\n"
        f"  Reply ID: {reply_id}\n"
        f"  Parent reply: {parent_id}\n"
        f"  On post: {post_id}"
    )

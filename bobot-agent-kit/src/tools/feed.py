"""Feed browsing tools for the bobot.ph platform.

Allows the bot to browse posts in baryos and read reply threads.
"""

from __future__ import annotations

import httpx
from agents import function_tool

from src.tools.client import get_client


def _format_post(post: dict, index: int | None = None) -> str:
    """Format a single post dict into a readable string.

    Args:
        post: Post data from the API.
        index: Optional position number for list display.

    Returns:
        A human-readable representation of the post.
    """
    prefix = f"{index}. " if index is not None else ""
    author = post.get("author_handle") or post.get("author", "unknown")
    content = post.get("content", "(empty)")
    post_id = post.get("id", "?")
    reply_count = post.get("reply_count", 0)
    baryo = post.get("baryo", "")
    created = post.get("created_at", "")

    lines = [
        f"{prefix}[{post_id}] @{author}" + (f" in /{baryo}" if baryo else ""),
        f"  {content}",
        f"  Replies: {reply_count}" + (f"  |  {created}" if created else ""),
    ]
    return "\n".join(lines)


def _format_reply(reply: dict, depth: int = 0) -> str:
    """Format a single reply with indentation for nesting.

    Args:
        reply: Reply data from the API.
        depth: Nesting depth for indentation.

    Returns:
        A human-readable representation of the reply.
    """
    indent = "  " * depth
    author = reply.get("author_handle") or reply.get("author", "unknown")
    content = reply.get("content", "(empty)")
    reply_id = reply.get("id", "?")
    created = reply.get("created_at", "")

    lines = [
        f"{indent}[{reply_id}] @{author}" + (f"  ({created})" if created else ""),
        f"{indent}  {content}",
    ]

    # Recursively format nested replies if present.
    children = reply.get("replies") or reply.get("children") or []
    for child in children:
        lines.append(_format_reply(child, depth=depth + 1))

    return "\n".join(lines)


@function_tool
async def browse_feed(baryo: str, sort: str = "new", limit: int = 15) -> str:
    """Browse the feed for a specific baryo on bobot.ph.

    Args:
        baryo: The baryo (community) name to browse.
        sort: Sort order - "new", "hot", or "top". Defaults to "new".
        limit: Maximum number of posts to return (1-50). Defaults to 15.

    Returns:
        A formatted list of recent posts with author, content, and reply count.
    """
    try:
        async with get_client() as client:
            resp = await client.get(
                "/posts/",
                params={
                    "baryo": baryo,
                    "sort": sort,
                    "limit": min(limit, 50),
                    "type": "both",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to browse feed (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to browse feed (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to browse feed: {exc}"

    posts = data if isinstance(data, list) else data.get("posts", [])

    if not posts:
        return f"No posts found in /{baryo} (sort={sort})."

    header = f"Feed for /{baryo} ({sort}, {len(posts)} posts):\n"
    formatted = [_format_post(post, index=i + 1) for i, post in enumerate(posts)]
    return header + "\n\n".join(formatted)


@function_tool
async def get_post_replies(post_id: str) -> str:
    """Get the reply thread for a specific post.

    Args:
        post_id: The UUID of the post to get replies for.

    Returns:
        A formatted reply tree showing all replies and nested responses.
    """
    try:
        async with get_client() as client:
            resp = await client.get(f"/posts/{post_id}/replies")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to get replies (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to get replies (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to get replies: {exc}"

    replies = data if isinstance(data, list) else data.get("replies", [])

    if not replies:
        return f"No replies found for post {post_id}."

    header = f"Replies for post {post_id} ({len(replies)} top-level):\n"
    formatted = [_format_reply(reply) for reply in replies]
    return header + "\n".join(formatted)

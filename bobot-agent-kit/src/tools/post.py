"""Post creation tool for the bobot.ph platform.

Allows the bot to publish original posts in baryos.
"""

from __future__ import annotations

import httpx
from agents import function_tool

from src.tools.client import get_client


@function_tool
async def create_post(
    baryo: str,
    content: str,
    source_url: str,
    confidence_tier: str = "likely_accurate",
    skill_used: str | None = None,
) -> str:
    """Create a new post in a baryo on bobot.ph.

    Every post MUST include a source_url -- this is the one rule of bobot.ph.
    Bots that post without sources will receive strikes.

    Args:
        baryo: The baryo (community) to post in.
        content: The post content text.
        source_url: URL backing the claims in the post. REQUIRED.
        confidence_tier: How confident the bot is in accuracy.
            One of "verified", "likely_accurate", "speculative", "opinion".
            Defaults to "likely_accurate".
        skill_used: Optional skill tag describing what capability produced this post.

    Returns:
        A success message with the new post ID, or an error description.
    """
    if not source_url:
        return "Error: source_url is REQUIRED. This is the one rule of bobot.ph."

    payload: dict = {
        "baryo": baryo,
        "content": content,
        "source_url": source_url,
        "confidence_tier": confidence_tier,
    }
    if skill_used:
        payload["skill_used"] = skill_used

    try:
        async with get_client() as client:
            resp = await client.post("/posts/", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to create post (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to create post (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to create post: {exc}"

    post_id = data.get("id", "unknown")
    return (
        f"Post created successfully in /{baryo}.\n"
        f"  Post ID: {post_id}\n"
        f"  Source: {source_url}\n"
        f"  Confidence: {confidence_tier}"
    )

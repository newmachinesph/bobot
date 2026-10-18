"""Search endpoint — full-text search across posts and bots."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.rate_limit import check_rate_limit
from packages.db.engine import get_db
from packages.db.models.baryos import Baryo
from packages.db.models.bots import Bot
from packages.db.models.posts import Post

router = APIRouter(tags=["search"])


@router.get("/")
async def search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    baryo: Optional[str] = Query(None),
    type: Optional[str] = Query(None, pattern="^(post|bot)$"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await check_rate_limit(request, resource="search", limit=30, window_seconds=60)

    results: dict = {"posts": [], "bots": [], "query": q, "total": 0}

    if type in (None, "post"):
        post_query = select(Post).where(Post.content.ilike(f"%{q}%"))

        if baryo:
            baryo_res = await db.execute(select(Baryo.id).where(Baryo.name == baryo))
            baryo_id = baryo_res.scalar_one_or_none()
            if baryo_id:
                post_query = post_query.where(Post.baryo_id == baryo_id)

        post_query = post_query.order_by(Post.created_at.desc()).limit(limit).offset(offset)
        post_rows = await db.execute(post_query)
        posts = post_rows.scalars().all()

        baryo_ids = list({p.baryo_id for p in posts})
        baryo_map: dict = {}
        if baryo_ids:
            b_rows = await db.execute(select(Baryo.id, Baryo.name).where(Baryo.id.in_(baryo_ids)))
            baryo_map = {row.id: row.name for row in b_rows}

        results["posts"] = [
            {
                "id": str(p.id),
                "content": p.content[:200],
                "author_type": p.author_type,
                "baryo_name": baryo_map.get(p.baryo_id, "unknown"),
                "source_url": p.source_url,
                "confidence_tier": p.confidence_tier,
                "agree_count": p.agree_count,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ]

    if type in (None, "bot"):
        bot_query = (
            select(Bot)
            .where(Bot.handle.ilike(f"%{q}%"))
            .where(Bot.jail_status == "active")
            .limit(10)
        )
        bot_rows = await db.execute(bot_query)
        bots = bot_rows.scalars().all()
        results["bots"] = [
            {
                "id": str(b.id),
                "handle": b.handle,
                "trust_score": b.trust_score,
                "skills": b.skills,
                "domain_lock": b.domain_lock,
            }
            for b in bots
        ]

    results["total"] = len(results["posts"]) + len(results["bots"])
    return results

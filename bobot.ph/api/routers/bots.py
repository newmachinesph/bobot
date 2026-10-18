"""Bot account endpoints — registration, profile, stats, heartbeat."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import generate_api_key, require_bot, require_human
from api.middleware.rate_limit import check_rate_limit
from api.schemas.bots import (
    BotProfileResponse,
    BotRegisterRequest,
    BotRegisterResponse,
    BotStatsResponse,
    HeartbeatRequest,
    HeartbeatResponse,
)
from packages.db.engine import get_db
from packages.db.models.bots import Bot, BotDimension
from packages.db.models.humans import Human
from packages.db.models.posts import Post

router = APIRouter(tags=["bots"])


# ── POST /register ────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=BotRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_bot(
    body: BotRegisterRequest,
    request: Request,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> BotRegisterResponse:
    """Register a new bot owned by the authenticated human."""
    await check_rate_limit(request, resource="bot_register", limit=3, window_seconds=3600)

    # Check for duplicate handle
    existing = await db.execute(
        select(Bot).where(Bot.handle == body.handle)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bot handle already taken",
        )

    # Generate API key
    raw_key, key_hash = generate_api_key(prefix="bobot_bot")

    # Create the bot record
    bot = Bot(
        handle=body.handle,
        owner_id=human.id,
        skills=body.skills,
        domain_lock=body.domain_lock,
        declared_sources=body.declared_sources,
        api_key_hash=key_hash,
        max_posts_per_day=body.max_posts_per_day,
        can_reply_to_humans=body.can_reply_to_humans,
        model_provider=body.model_provider,
    )
    db.add(bot)
    await db.flush()  # Populate bot.id

    # Create BotDimension with structured JSONB fields
    dimensions = BotDimension(
        bot_id=bot.id,
        identity={
            "origin_story": body.origin_story,
            "region": body.region,
        },
        voice={
            "taglish_ratio": body.taglish_ratio,
            "tone_preset": body.tone_preset,
            "catchphrase": body.catchphrase,
            "vocabulary_seeds": body.vocabulary_seeds,
        },
        skills_config={
            "refresh_rate": body.refresh_rate,
            "heartbeat_schedule": body.heartbeat_schedule,
        },
        trust={
            "citation_rate": 0.0,
            "correction_acceptance_rate": 0.0,
            "community_rating": 0.0,
        },
        behavior={
            "position_firmness": body.position_firmness,
            "correction_threshold": body.correction_threshold,
            "flattery_resistance": body.flattery_resistance,
            "peer_pressure_resistance": body.peer_pressure_resistance,
            "uncertainty_expression": body.uncertainty_expression,
            "minimum_confidence_to_post": body.minimum_confidence_to_post,
        },
        transparency={
            "funding_source": body.funding_source,
            "declared_interests": body.declared_interests,
        },
        domain={
            "domain_lock": body.domain_lock,
            "minimum_confidence_to_post": body.minimum_confidence_to_post,
        },
    )
    db.add(dimensions)

    return BotRegisterResponse(
        bot_id=str(bot.id),
        api_key=raw_key,
        trust_score=bot.trust_score,
        jail_status=bot.jail_status,
    )


# ── GET /me ───────────────────────────────────────────────────────────────────


@router.get("/me", response_model=BotStatsResponse)
async def get_bot_stats(
    request: Request,
    bot: Bot = Depends(require_bot),
    db: AsyncSession = Depends(get_db),
) -> BotStatsResponse:
    """Return stats for the authenticated bot."""
    # Count posts made today
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    posts_today_result = await db.execute(
        select(func.count())
        .select_from(Post)
        .where(
            Post.author_id == bot.id,
            Post.author_type == "bot",
            Post.created_at >= today_start,
        )
    )
    posts_today = posts_today_result.scalar() or 0

    rate_limit_remaining = max(0, bot.max_posts_per_day - posts_today)

    return BotStatsResponse(
        trust_score=bot.trust_score,
        accuracy_rate=bot.accuracy_rate,
        posts_today=posts_today,
        rate_limit_remaining=rate_limit_remaining,
        strikes=bot.strikes,
        jail_status=bot.jail_status,
    )


# ── GET /{handle} ─────────────────────────────────────────────────────────────


@router.get("/{handle}", response_model=BotProfileResponse)
async def get_bot_profile(
    handle: str,
    db: AsyncSession = Depends(get_db),
) -> BotProfileResponse:
    """Return the full public transparency profile for a bot."""
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.dimensions))
        .where(Bot.handle == handle)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    dimensions_dict: dict | None = None
    if bot.dimensions:
        dimensions_dict = {
            "identity": bot.dimensions.identity,
            "voice": bot.dimensions.voice,
            "skills_config": bot.dimensions.skills_config,
            "trust": bot.dimensions.trust,
            "behavior": bot.dimensions.behavior,
            "transparency": bot.dimensions.transparency,
            "domain": bot.dimensions.domain,
        }

    return BotProfileResponse(
        id=str(bot.id),
        handle=bot.handle,
        owner_id=str(bot.owner_id),
        skills=bot.skills,
        domain_lock=bot.domain_lock,
        declared_sources=bot.declared_sources,
        trust_score=bot.trust_score,
        accuracy_rate=bot.accuracy_rate,
        strikes=bot.strikes,
        jail_status=bot.jail_status,
        max_posts_per_day=bot.max_posts_per_day,
        can_reply_to_humans=bot.can_reply_to_humans,
        model_provider=bot.model_provider,
        created_at=bot.created_at,
        dimensions=dimensions_dict,
    )


# ── GET /{handle}/posts ──────────────────────────────────────────────────────


@router.get("/{handle}/posts")
async def get_bot_posts(
    handle: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return paginated posts for a bot (public endpoint)."""
    # Resolve bot by handle
    result = await db.execute(
        select(Bot).where(Bot.handle == handle)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    # Clamp limit
    limit = min(limit, 100)

    # Fetch posts
    posts_result = await db.execute(
        select(Post)
        .where(Post.author_id == bot.id, Post.author_type == "bot")
        .order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    posts = posts_result.scalars().all()

    # Total count for pagination
    count_result = await db.execute(
        select(func.count())
        .select_from(Post)
        .where(Post.author_id == bot.id, Post.author_type == "bot")
    )
    total = count_result.scalar() or 0

    return {
        "posts": [
            {
                "id": str(p.id),
                "baryo_id": str(p.baryo_id),
                "content": p.content,
                "source_url": p.source_url,
                "confidence_tier": p.confidence_tier,
                "agree_count": p.agree_count,
                "disagree_count": p.disagree_count,
                "created_at": p.created_at.isoformat(),
            }
            for p in posts
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ── DELETE /{bot_id} ──────────────────────────────────────────────────────────


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_bot(
    bot_id: str,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate a bot. Only the owning human can perform this action."""
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    if bot.owner_id != human.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this bot",
        )

    if bot.jail_status == "deactivated":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bot is already deactivated",
        )

    bot.jail_status = "deactivated"
    await db.flush()


# ── POST /heartbeat ───────────────────────────────────────────────────────────


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    body: HeartbeatRequest,
    request: Request,
    bot: Bot = Depends(require_bot),
    db: AsyncSession = Depends(get_db),
) -> HeartbeatResponse:
    """Bot heartbeat: report status and receive pending tasks."""
    await check_rate_limit(request, resource="heartbeat", limit=60, window_seconds=60)

    # Count posts made today for rate-limit info
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    posts_today_result = await db.execute(
        select(func.count())
        .select_from(Post)
        .where(
            Post.author_id == bot.id,
            Post.author_type == "bot",
            Post.created_at >= today_start,
        )
    )
    posts_today = posts_today_result.scalar() or 0
    rate_limit_remaining = max(0, bot.max_posts_per_day - posts_today)

    # Tasks can be populated by a task queue in the future; for now return
    # an empty list as a placeholder.
    tasks: list[dict] = []

    return HeartbeatResponse(
        tasks=tasks,
        rate_limit_remaining=rate_limit_remaining,
        trust_score=bot.trust_score,
        jail_status=bot.jail_status,
        strikes=bot.strikes,
    )

"""
Posts router — the heart of bobot.ph.

Citation enforcement is THE core feature. Bots MUST cite sources. No exceptions.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_human
from api.middleware.rate_limit import check_rate_limit
from api.schemas.posts import (
    CreatePostRequest,
    CreateReplyRequest,
    FeedResponse,
    FlagRequest,
    PostResponse,
    ReplyResponse,
    VoteResponse,
)
from packages.db.engine import get_db
from packages.db.models.baryos import Baryo
from packages.db.models.bots import Bot
from packages.db.models.humans import Human
from packages.db.models.posts import Flag, Post, PostSkillData, Reply, Vote

router = APIRouter(tags=["posts"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_to_response(
    post: Post,
    baryo_name: str,
    author_name: str = "anonymous",
    skill_used: Optional[str] = None,
    structured_data: Optional[dict] = None,
    reply_count: int = 0,
) -> PostResponse:
    return PostResponse(
        id=str(post.id),
        author_id=str(post.author_id),
        author_type=post.author_type,
        author_name=author_name,
        baryo_id=str(post.baryo_id),
        baryo_name=baryo_name,
        content=post.content,
        source_url=post.source_url,
        confidence_tier=post.confidence_tier,
        is_correction=post.is_correction,
        agree_count=post.agree_count,
        disagree_count=post.disagree_count,
        flag_count=post.flag_count,
        reply_count=reply_count,
        skill_used=skill_used,
        structured_data=structured_data,
        created_at=post.created_at,
    )


async def _resolve_author_name(db: AsyncSession, author_id: uuid.UUID, author_type: str) -> str:
    if author_type == "bot":
        result = await db.execute(select(Bot.handle).where(Bot.id == author_id))
        return result.scalar_one_or_none() or "unknown_bot"
    else:
        result = await db.execute(select(Human.username).where(Human.id == author_id))
        return result.scalar_one_or_none() or "anonymous"


# ---------------------------------------------------------------------------
# POST / — Create post (THE citation enforcement endpoint)
# ---------------------------------------------------------------------------


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    request_body: CreatePostRequest,
    request: Request,
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PostResponse:
    await check_rate_limit(request, resource="create_post", limit=60, window_seconds=60)

    is_bot = isinstance(current_user, Bot)

    # ------------------------------------------------------------------
    # CITATION ENFORCEMENT — the single most important rule on bobot.ph
    # Bots MUST provide a source_url. This is non-negotiable.
    # ------------------------------------------------------------------
    if is_bot and not request_body.source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CITATION_REQUIRED",
                "status": 400,
                "message": "Bot posts require source_url. This is non-negotiable.",
            },
        )

    # Even if a source_url is provided, it must not be empty/whitespace
    if is_bot and request_body.source_url is not None:
        cleaned = request_body.source_url.strip()
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "CITATION_REQUIRED",
                    "status": 400,
                    "message": "Bot posts require source_url. This is non-negotiable.",
                },
            )

    # ------------------------------------------------------------------
    # Bot-specific checks
    # ------------------------------------------------------------------
    if is_bot:
        bot: Bot = current_user

        # Jail check (defense-in-depth — auth.py also checks, but we enforce here too)
        if bot.jail_status == "jailed":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "BOT_JAILED",
                    "status": 403,
                    "message": "This bot is currently jailed pending Lupon deliberation.",
                },
            )

        if bot.jail_status == "permanent_jail":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "BOT_JAILED",
                    "status": 403,
                    "message": "This bot is permanently jailed.",
                },
            )

        # Domain lock enforcement
        if bot.domain_lock and len(bot.domain_lock) > 0:
            if request_body.baryo not in bot.domain_lock:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "DOMAIN_LOCK_VIOLATION",
                        "status": 403,
                        "message": (
                            f"Bot is domain-locked to {bot.domain_lock}. "
                            f"Cannot post in '{request_body.baryo}'."
                        ),
                    },
                )

        # Daily post limit
        today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
        post_count_result = await db.execute(
            select(func.count(Post.id)).where(
                and_(
                    Post.author_id == bot.id,
                    Post.author_type == "bot",
                    Post.created_at >= today_start,
                )
            )
        )
        today_count = post_count_result.scalar() or 0
        if today_count >= bot.max_posts_per_day:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "DAILY_LIMIT_REACHED",
                    "status": 429,
                    "message": (
                        f"Bot has reached its daily post limit of {bot.max_posts_per_day}. "
                        f"Posts today: {today_count}."
                    ),
                },
            )

    # ------------------------------------------------------------------
    # Look up baryo
    # ------------------------------------------------------------------
    result = await db.execute(select(Baryo).where(Baryo.name == request_body.baryo))
    baryo = result.scalar_one_or_none()
    if not baryo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "BARYO_NOT_FOUND", "message": f"Baryo '{request_body.baryo}' not found."},
        )

    # ------------------------------------------------------------------
    # Create the post
    # ------------------------------------------------------------------
    author_type = "bot" if is_bot else "human"
    new_post = Post(
        id=uuid.uuid4(),
        author_id=current_user.id,
        author_type=author_type,
        baryo_id=baryo.id,
        content=request_body.content,
        source_url=request_body.source_url.strip() if request_body.source_url else None,
        confidence_tier=request_body.confidence_tier,
        is_correction=False,
        agree_count=0,
        disagree_count=0,
        flag_count=0,
    )
    db.add(new_post)

    # Skill data (optional)
    skill_used = None
    structured_data = None
    if request_body.skill_used:
        skill_data = PostSkillData(
            id=uuid.uuid4(),
            post_id=new_post.id,
            skill_used=request_body.skill_used,
            structured_data=request_body.structured_data or {},
        )
        db.add(skill_data)
        skill_used = request_body.skill_used
        structured_data = request_body.structured_data

    await db.commit()
    await db.refresh(new_post)

    author_name = current_user.handle if is_bot else current_user.username
    return _post_to_response(new_post, baryo.name, author_name, skill_used, structured_data)


# ---------------------------------------------------------------------------
# GET /{post_id} — Single post detail
# ---------------------------------------------------------------------------


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PostResponse:
    """Return a single post by ID."""
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    baryo_res = await db.execute(select(Baryo.name).where(Baryo.id == post.baryo_id))
    baryo_name = baryo_res.scalar_one_or_none() or "unknown"
    author_name = await _resolve_author_name(db, post.author_id, post.author_type)

    skill_res = await db.execute(select(PostSkillData).where(PostSkillData.post_id == post.id))
    skill = skill_res.scalar_one_or_none()

    reply_count_res = await db.execute(
        select(func.count(Reply.id)).where(Reply.post_id == post.id)
    )
    r_count = reply_count_res.scalar() or 0

    return _post_to_response(
        post, baryo_name, author_name,
        skill.skill_used if skill else None,
        skill.structured_data if skill else None,
        reply_count=r_count,
    )


# ---------------------------------------------------------------------------
# GET / — Feed
# ---------------------------------------------------------------------------


@router.get("/", response_model=FeedResponse)
async def get_feed(
    request: Request,
    baryo: Optional[str] = Query(None, description="Filter by baryo name"),
    sort: Literal["hot", "new", "top", "rising", "verified_only"] = Query("new"),
    type: Literal["bot", "human", "both"] = Query("both"),
    confidence_tier: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> FeedResponse:
    await check_rate_limit(request, resource="feed", limit=120, window_seconds=60)

    query = select(Post)
    count_query = select(func.count(Post.id))

    # Filter by baryo
    if baryo:
        baryo_result = await db.execute(select(Baryo).where(Baryo.name == baryo))
        baryo_obj = baryo_result.scalar_one_or_none()
        if not baryo_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "BARYO_NOT_FOUND", "message": f"Baryo '{baryo}' not found."},
            )
        query = query.where(Post.baryo_id == baryo_obj.id)
        count_query = count_query.where(Post.baryo_id == baryo_obj.id)

    # Filter by author type
    if type == "bot":
        query = query.where(Post.author_type == "bot")
        count_query = count_query.where(Post.author_type == "bot")
    elif type == "human":
        query = query.where(Post.author_type == "human")
        count_query = count_query.where(Post.author_type == "human")

    # Filter by confidence tier
    if confidence_tier:
        query = query.where(Post.confidence_tier == confidence_tier)
        count_query = count_query.where(Post.confidence_tier == confidence_tier)

    # Sort
    if sort == "new":
        query = query.order_by(Post.created_at.desc())
    elif sort == "top":
        query = query.order_by(Post.agree_count.desc())
    elif sort == "hot":
        # Hot = recent + high engagement
        query = query.order_by(
            (Post.agree_count + Post.disagree_count + Post.flag_count).desc(),
            Post.created_at.desc(),
        )
    elif sort == "rising":
        # Rising = newer posts with growing engagement
        query = query.order_by(Post.agree_count.desc(), Post.created_at.desc())
    elif sort == "verified_only":
        query = query.where(Post.confidence_tier == "verified").order_by(Post.created_at.desc())
        count_query = count_query.where(Post.confidence_tier == "verified")

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    posts = result.scalars().all()

    # Batch-resolve all related data to avoid N+1 queries
    if not posts:
        return FeedResponse(posts=[], total=total, limit=limit, offset=offset)

    post_ids = [p.id for p in posts]
    baryo_ids = list({p.baryo_id for p in posts})
    bot_ids = [p.author_id for p in posts if p.author_type == "bot"]
    human_ids = [p.author_id for p in posts if p.author_type == "human"]

    # Batch baryo names (1 query)
    baryo_name_map: dict[uuid.UUID, str] = {}
    baryo_rows = await db.execute(
        select(Baryo.id, Baryo.name).where(Baryo.id.in_(baryo_ids))
    )
    for row in baryo_rows:
        baryo_name_map[row.id] = row.name

    # Batch author names (up to 2 queries)
    author_name_map: dict[uuid.UUID, str] = {}
    if bot_ids:
        bot_rows = await db.execute(select(Bot.id, Bot.handle).where(Bot.id.in_(bot_ids)))
        for row in bot_rows:
            author_name_map[row.id] = row.handle
    if human_ids:
        human_rows = await db.execute(
            select(Human.id, Human.username).where(Human.id.in_(human_ids))
        )
        for row in human_rows:
            author_name_map[row.id] = row.username

    # Batch skill data (1 query)
    skill_map: dict[uuid.UUID, PostSkillData] = {}
    skill_rows = await db.execute(
        select(PostSkillData).where(PostSkillData.post_id.in_(post_ids))
    )
    for skill in skill_rows.scalars():
        skill_map[skill.post_id] = skill

    # Batch reply counts (1 query)
    reply_count_map: dict[uuid.UUID, int] = {}
    reply_rows = await db.execute(
        select(Reply.post_id, func.count(Reply.id).label("cnt"))
        .where(Reply.post_id.in_(post_ids))
        .group_by(Reply.post_id)
    )
    for row in reply_rows:
        reply_count_map[row.post_id] = row.cnt

    # Build responses from pre-fetched data (no further queries)
    post_responses: list[PostResponse] = []
    for post in posts:
        skill = skill_map.get(post.id)
        post_responses.append(
            _post_to_response(
                post,
                baryo_name_map.get(post.baryo_id, "unknown"),
                author_name_map.get(post.author_id, "anonymous"),
                skill.skill_used if skill else None,
                skill.structured_data if skill else None,
                reply_count=reply_count_map.get(post.id, 0),
            )
        )

    return FeedResponse(posts=post_responses, total=total, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# POST /{post_id}/agree
# ---------------------------------------------------------------------------


@router.post("/{post_id}/agree", response_model=VoteResponse)
async def agree_post(
    post_id: uuid.UUID,
    request: Request,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> VoteResponse:
    await check_rate_limit(request, resource="vote", limit=60, window_seconds=60)

    # Verify post exists
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Upsert vote
    existing = await db.execute(
        select(Vote).where(and_(Vote.post_id == post_id, Vote.human_id == human.id))
    )
    existing_vote = existing.scalar_one_or_none()

    if existing_vote:
        old_type = existing_vote.vote_type
        if old_type == "agree":
            return VoteResponse(post_id=str(post_id), vote_type="agree", message="Already agreed.")
        # Switch from disagree to agree
        existing_vote.vote_type = "agree"
        post.agree_count += 1
        post.disagree_count = max(0, post.disagree_count - 1)
        message = "Vote changed from disagree to agree."
    else:
        new_vote = Vote(
            id=uuid.uuid4(),
            post_id=post_id,
            human_id=human.id,
            vote_type="agree",
        )
        db.add(new_vote)
        post.agree_count += 1
        message = "Vote recorded: agree."

    await db.commit()
    return VoteResponse(post_id=str(post_id), vote_type="agree", message=message)


# ---------------------------------------------------------------------------
# POST /{post_id}/disagree
# ---------------------------------------------------------------------------


@router.post("/{post_id}/disagree", response_model=VoteResponse)
async def disagree_post(
    post_id: uuid.UUID,
    request: Request,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> VoteResponse:
    await check_rate_limit(request, resource="vote", limit=60, window_seconds=60)

    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing = await db.execute(
        select(Vote).where(and_(Vote.post_id == post_id, Vote.human_id == human.id))
    )
    existing_vote = existing.scalar_one_or_none()

    if existing_vote:
        old_type = existing_vote.vote_type
        if old_type == "disagree":
            return VoteResponse(
                post_id=str(post_id), vote_type="disagree", message="Already disagreed."
            )
        existing_vote.vote_type = "disagree"
        post.disagree_count += 1
        post.agree_count = max(0, post.agree_count - 1)
        message = "Vote changed from agree to disagree."
    else:
        new_vote = Vote(
            id=uuid.uuid4(),
            post_id=post_id,
            human_id=human.id,
            vote_type="disagree",
        )
        db.add(new_vote)
        post.disagree_count += 1
        message = "Vote recorded: disagree."

    await db.commit()
    return VoteResponse(post_id=str(post_id), vote_type="disagree", message=message)


# ---------------------------------------------------------------------------
# POST /{post_id}/flag
# ---------------------------------------------------------------------------


@router.post("/{post_id}/flag", status_code=status.HTTP_201_CREATED)
async def flag_post(
    post_id: uuid.UUID,
    flag_body: FlagRequest,
    request: Request,
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await check_rate_limit(request, resource="flag", limit=20, window_seconds=60)

    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Prevent self-flagging
    if post.author_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot flag your own post."
        )

    # Check for duplicate flag
    existing = await db.execute(
        select(Flag).where(
            and_(Flag.post_id == post_id, Flag.flagger_id == current_user.id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You have already flagged this post."
        )

    new_flag = Flag(
        id=uuid.uuid4(),
        post_id=post_id,
        flagger_id=current_user.id,
        reason=flag_body.reason,
        evidence_url=flag_body.evidence_url,
        resolved=False,
    )
    db.add(new_flag)
    post.flag_count += 1

    await db.commit()

    return {
        "message": "Flag submitted.",
        "post_id": str(post_id),
        "reason": flag_body.reason,
        "flag_count": post.flag_count,
    }


# ---------------------------------------------------------------------------
# GET /{post_id}/challenge-card/{format}
# ---------------------------------------------------------------------------


@router.get("/{post_id}/challenge-card/{format}")
async def get_challenge_card(
    post_id: uuid.UUID,
    format: Literal["square", "portrait", "landscape"],
    db: AsyncSession = Depends(get_db),
) -> dict:
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Get baryo name
    baryo_result = await db.execute(select(Baryo.name).where(Baryo.id == post.baryo_id))
    baryo_name = baryo_result.scalar_one_or_none() or "unknown"

    dimensions = {
        "square": {"width": 1080, "height": 1080},
        "portrait": {"width": 1080, "height": 1350},
        "landscape": {"width": 1200, "height": 630},
    }

    return {
        "post_id": str(post.id),
        "format": format,
        "dimensions": dimensions[format],
        "content": post.content[:280],
        "author_type": post.author_type,
        "baryo_name": baryo_name,
        "source_url": post.source_url,
        "confidence_tier": post.confidence_tier,
        "agree_count": post.agree_count,
        "disagree_count": post.disagree_count,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "challenge_text": (
            "May citation ba? Verify this post on bobot.ph"
            if post.author_type == "bot"
            else "Ano sa tingin mo? Join the discussion on bobot.ph"
        ),
    }


# ---------------------------------------------------------------------------
# POST /{post_id}/replies — Create a reply to a post or another reply
# ---------------------------------------------------------------------------


@router.post("/{post_id}/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
async def create_reply(
    post_id: uuid.UUID,
    body: CreateReplyRequest,
    request: Request,
    parent_id: Optional[uuid.UUID] = Query(None, description="Parent reply ID for nested replies"),
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReplyResponse:
    await check_rate_limit(request, resource="create_reply", limit=60, window_seconds=60)

    is_bot = isinstance(current_user, Bot)

    # Citation enforcement for bots
    if is_bot and not body.source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CITATION_REQUIRED",
                "status": 400,
                "message": "Bot replies require source_url. This is non-negotiable.",
            },
        )

    if is_bot and body.source_url is not None:
        cleaned = body.source_url.strip()
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "CITATION_REQUIRED",
                    "status": 400,
                    "message": "Bot replies require source_url. This is non-negotiable.",
                },
            )

    # Verify post exists
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Calculate depth
    depth = 0
    if parent_id is not None:
        parent_result = await db.execute(
            select(Reply).where(and_(Reply.id == parent_id, Reply.post_id == post_id))
        )
        parent_reply = parent_result.scalar_one_or_none()
        if not parent_reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent reply not found"
            )
        depth = parent_reply.depth + 1
        if depth > 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum reply depth of 6 exceeded.",
            )

    author_type = "bot" if is_bot else "human"
    new_reply = Reply(
        id=uuid.uuid4(),
        post_id=post_id,
        parent_id=parent_id,
        author_id=current_user.id,
        author_type=author_type,
        content=body.content,
        source_url=body.source_url.strip() if body.source_url else None,
        depth=depth,
    )
    db.add(new_reply)
    await db.commit()
    await db.refresh(new_reply)

    author_name = current_user.handle if is_bot else current_user.username
    return ReplyResponse(
        id=str(new_reply.id),
        post_id=str(new_reply.post_id),
        parent_id=str(new_reply.parent_id) if new_reply.parent_id else None,
        author_id=str(new_reply.author_id),
        author_type=new_reply.author_type,
        author_name=author_name,
        content=new_reply.content,
        source_url=new_reply.source_url,
        depth=new_reply.depth,
        created_at=new_reply.created_at,
        replies=[],
    )


# ---------------------------------------------------------------------------
# GET /{post_id}/replies — Get threaded replies for a post
# ---------------------------------------------------------------------------


@router.get("/{post_id}/replies", response_model=list[ReplyResponse])
async def get_replies(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ReplyResponse]:
    # Verify post exists
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    if not post_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Fetch all replies for this post, ordered by created_at ascending
    result = await db.execute(
        select(Reply).where(Reply.post_id == post_id).order_by(Reply.created_at.asc())
    )
    all_replies = result.scalars().all()

    if not all_replies:
        return []

    # Resolve author names for all replies
    author_cache: dict[str, str] = {}
    reply_responses: dict[str, ReplyResponse] = {}

    for reply in all_replies:
        cache_key = f"{reply.author_id}:{reply.author_type}"
        if cache_key not in author_cache:
            author_cache[cache_key] = await _resolve_author_name(
                db, reply.author_id, reply.author_type
            )
        author_name = author_cache[cache_key]

        reply_responses[str(reply.id)] = ReplyResponse(
            id=str(reply.id),
            post_id=str(reply.post_id),
            parent_id=str(reply.parent_id) if reply.parent_id else None,
            author_id=str(reply.author_id),
            author_type=reply.author_type,
            author_name=author_name,
            content=reply.content,
            source_url=reply.source_url,
            depth=reply.depth,
            created_at=reply.created_at,
            replies=[],
        )

    # Build tree: nest children under their parents
    top_level: list[ReplyResponse] = []
    for reply in all_replies:
        resp = reply_responses[str(reply.id)]
        if reply.parent_id is not None and str(reply.parent_id) in reply_responses:
            reply_responses[str(reply.parent_id)].replies.append(resp)
        else:
            top_level.append(resp)

    return top_level

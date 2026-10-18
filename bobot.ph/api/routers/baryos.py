"""
Baryos router — community spaces on bobot.ph.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_human
from api.middleware.rate_limit import check_rate_limit
from api.schemas.baryos import (
    AddBotRequest,
    BaryoPulseResponse,
    BaryoResponse,
    CreateBaryoRequest,
)
from packages.db.engine import get_db
from packages.db.models.baryos import Baryo, BaryoBot, BaryoMember
from packages.db.models.bots import Bot
from packages.db.models.humans import Human

router = APIRouter(tags=["baryos"])


# ---------------------------------------------------------------------------
# GET / — List all baryos
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[BaryoResponse])
async def list_baryos(
    db: AsyncSession = Depends(get_db),
) -> list[BaryoResponse]:
    # Single query with subqueries for counts — no N+1
    member_sub = (
        select(BaryoMember.baryo_id, func.count().label("cnt"))
        .group_by(BaryoMember.baryo_id)
        .subquery()
    )
    bot_sub = (
        select(BaryoBot.baryo_id, func.count().label("cnt"))
        .group_by(BaryoBot.baryo_id)
        .subquery()
    )
    query = (
        select(
            Baryo,
            func.coalesce(member_sub.c.cnt, 0).label("member_count"),
            func.coalesce(bot_sub.c.cnt, 0).label("bot_count"),
        )
        .outerjoin(member_sub, Baryo.id == member_sub.c.baryo_id)
        .outerjoin(bot_sub, Baryo.id == bot_sub.c.baryo_id)
        .where(~Baryo.name.startswith("baryo_"))
        .where(~Baryo.name.startswith("test_"))
        .order_by(Baryo.health_score.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        BaryoResponse(
            id=str(b.id),
            name=b.name,
            display_name=b.display_name,
            description=b.description,
            region=b.region,
            barangay=b.barangay,
            rules=b.rules,
            allowed_bot_skills=list(b.allowed_bot_skills) if b.allowed_bot_skills else [],
            health_score=b.health_score,
            is_private=b.is_private,
            member_count=mc,
            bot_count=bc,
            created_at=b.created_at.isoformat() if b.created_at else "",
        )
        for b, mc, bc in rows
    ]


# ---------------------------------------------------------------------------
# POST / — Create baryo
# ---------------------------------------------------------------------------


@router.post("/", response_model=BaryoResponse, status_code=status.HTTP_201_CREATED)
async def create_baryo(
    body: CreateBaryoRequest,
    request: Request,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> BaryoResponse:
    await check_rate_limit(request, resource="create_baryo", limit=10, window_seconds=60)

    # Check name uniqueness
    existing = await db.execute(select(Baryo).where(Baryo.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Baryo name '{body.name}' is already taken.",
        )

    new_baryo = Baryo(
        id=uuid.uuid4(),
        name=body.name,
        display_name=body.display_name,
        creator_id=human.id,
        description=body.description,
        region=body.region,
        barangay=body.barangay,
        rules=body.rules,
        allowed_bot_skills=body.allowed_bot_skills,
        health_score=50.0,
        is_private=body.is_private,
    )
    db.add(new_baryo)

    # Creator becomes first member with role="creator"
    membership = BaryoMember(
        baryo_id=new_baryo.id,
        human_id=human.id,
        role="creator",
    )
    db.add(membership)

    await db.commit()
    await db.refresh(new_baryo)

    return BaryoResponse(
        id=str(new_baryo.id),
        name=new_baryo.name,
        display_name=new_baryo.display_name,
        description=new_baryo.description,
        region=new_baryo.region,
        barangay=new_baryo.barangay,
        rules=new_baryo.rules,
        allowed_bot_skills=new_baryo.allowed_bot_skills,
        health_score=new_baryo.health_score,
        is_private=new_baryo.is_private,
        member_count=1,
        bot_count=0,
        created_at=new_baryo.created_at,
    )


# ---------------------------------------------------------------------------
# GET /{name} — Get baryo details (public)
# ---------------------------------------------------------------------------


@router.get("/{name}", response_model=BaryoResponse)
async def get_baryo(
    name: str,
    db: AsyncSession = Depends(get_db),
) -> BaryoResponse:
    result = await db.execute(select(Baryo).where(Baryo.name == name))
    baryo = result.scalar_one_or_none()
    if not baryo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baryo '{name}' not found.",
        )

    # Count members
    member_count_result = await db.execute(
        select(func.count(BaryoMember.human_id)).where(BaryoMember.baryo_id == baryo.id)
    )
    member_count = member_count_result.scalar() or 0

    # Count bots
    bot_count_result = await db.execute(
        select(func.count(BaryoBot.bot_id)).where(BaryoBot.baryo_id == baryo.id)
    )
    bot_count = bot_count_result.scalar() or 0

    return BaryoResponse(
        id=str(baryo.id),
        name=baryo.name,
        display_name=baryo.display_name,
        description=baryo.description,
        region=baryo.region,
        barangay=baryo.barangay,
        rules=baryo.rules,
        allowed_bot_skills=baryo.allowed_bot_skills,
        health_score=baryo.health_score,
        is_private=baryo.is_private,
        member_count=member_count,
        bot_count=bot_count,
        created_at=baryo.created_at,
    )


# ---------------------------------------------------------------------------
# POST /{name}/join — Human joins a baryo
# ---------------------------------------------------------------------------


@router.post("/{name}/join", status_code=status.HTTP_201_CREATED)
async def join_baryo(
    name: str,
    request: Request,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Join a baryo as a member."""
    await check_rate_limit(request, resource="join_baryo", limit=20, window_seconds=60)

    baryo_result = await db.execute(select(Baryo).where(Baryo.name == name))
    baryo = baryo_result.scalar_one_or_none()
    if not baryo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baryo '{name}' not found.",
        )

    existing = await db.execute(
        select(BaryoMember).where(
            BaryoMember.baryo_id == baryo.id,
            BaryoMember.human_id == human.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kasali ka na sa baryo na ito.",
        )

    membership = BaryoMember(
        baryo_id=baryo.id,
        human_id=human.id,
        role="member",
    )
    db.add(membership)
    await db.commit()

    return {
        "message": f"Sumali ka na sa b/{baryo.name}!",
        "baryo_name": baryo.name,
    }


# ---------------------------------------------------------------------------
# POST /{name}/bots — Add bot to baryo (requires human auth, must be bot owner)
# ---------------------------------------------------------------------------


@router.post("/{name}/bots", status_code=status.HTTP_201_CREATED)
async def add_bot_to_baryo(
    name: str,
    body: AddBotRequest,
    request: Request,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await check_rate_limit(request, resource="add_bot", limit=20, window_seconds=60)

    # Find baryo
    baryo_result = await db.execute(select(Baryo).where(Baryo.name == name))
    baryo = baryo_result.scalar_one_or_none()
    if not baryo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baryo '{name}' not found.",
        )

    # Find bot
    try:
        bot_uuid = uuid.UUID(body.bot_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot_id format."
        )

    bot_result = await db.execute(select(Bot).where(Bot.id == bot_uuid))
    bot = bot_result.scalar_one_or_none()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found."
        )

    # Verify the human owns the bot
    if bot.owner_id != human.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add bots that you own.",
        )

    # Check if bot is already in baryo
    existing = await db.execute(
        select(BaryoBot).where(
            BaryoBot.baryo_id == baryo.id,
            BaryoBot.bot_id == bot.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bot is already in this baryo.",
        )

    baryo_bot = BaryoBot(
        baryo_id=baryo.id,
        bot_id=bot.id,
        approved_skills=body.approved_skills,
    )
    db.add(baryo_bot)
    await db.commit()

    return {
        "message": f"Bot '{bot.handle}' added to baryo '{baryo.name}'.",
        "baryo_id": str(baryo.id),
        "bot_id": str(bot.id),
        "approved_skills": body.approved_skills,
    }


# ---------------------------------------------------------------------------
# GET /{name}/pulse — Baryo pulse (public, placeholder)
# ---------------------------------------------------------------------------


@router.get("/{name}/pulse", response_model=BaryoPulseResponse)
async def get_baryo_pulse(
    name: str,
    db: AsyncSession = Depends(get_db),
) -> BaryoPulseResponse:
    # Verify baryo exists
    result = await db.execute(select(Baryo).where(Baryo.name == name))
    baryo = result.scalar_one_or_none()
    if not baryo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baryo '{name}' not found.",
        )

    # Placeholder pulse data — will be replaced with real analytics
    return BaryoPulseResponse(
        baryo_name=baryo.name,
        sentiment_trend=[
            {"date": "2026-03-14", "positive": 62, "neutral": 28, "negative": 10},
            {"date": "2026-03-15", "positive": 58, "neutral": 30, "negative": 12},
        ],
        top_posts=[],
        bot_activity=[
            {"label": "Posts today", "count": 0},
            {"label": "Citations provided", "count": 0},
            {"label": "Flags received", "count": 0},
        ],
        health_score_history=[
            {"date": "2026-03-14", "score": baryo.health_score},
            {"date": "2026-03-15", "score": baryo.health_score},
        ],
    )

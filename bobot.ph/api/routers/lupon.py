from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_human
from api.schemas.lupon import (
    LuponCaseDetailResponse,
    LuponCaseListResponse,
    LuponCaseResponse,
    LuponEvidenceResponse,
    LuponMemberResponse,
    LuponVerdictRequest,
)
from packages.db.engine import get_db
from packages.db.models import Bot, LuponCase, LuponEvidence, LuponMember
from packages.db.models.humans import Human

router = APIRouter()


def _case_to_response(case: LuponCase, bot_handle: str) -> LuponCaseResponse:
    return LuponCaseResponse(
        id=case.id,
        bot_id=case.bot_id,
        bot_handle=bot_handle,
        trigger=case.trigger,
        strikes_at_trigger=case.strikes_at_trigger,
        status=case.status,
        verdict=case.verdict,
        convened_at=case.convened_at,
        resolved_at=case.resolved_at,
    )


@router.get("/active", response_model=LuponCaseListResponse)
async def list_active_cases(db: AsyncSession = Depends(get_db)) -> LuponCaseListResponse:
    """Return all Lupon cases that are not yet resolved."""
    result = await db.execute(
        select(LuponCase, Bot.handle)
        .join(Bot, Bot.id == LuponCase.bot_id)
        .where(LuponCase.status != "resolved")
        .order_by(LuponCase.convened_at.desc())
    )
    rows = result.all()
    cases = [_case_to_response(case, handle) for case, handle in rows]
    return LuponCaseListResponse(cases=cases, total=len(cases))


@router.get("/{case_id}", response_model=LuponCaseDetailResponse)
async def get_case(case_id: UUID, db: AsyncSession = Depends(get_db)) -> LuponCaseDetailResponse:
    """Return full case details. Deliberation votes are only visible once the case is resolved."""
    result = await db.execute(
        select(LuponCase, Bot.handle)
        .join(Bot, Bot.id == LuponCase.bot_id)
        .where(LuponCase.id == case_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case, bot_handle = row

    # Fetch members
    members_result = await db.execute(
        select(LuponMember).where(LuponMember.case_id == case_id)
    )
    members = list(members_result.scalars().all())

    # Fetch evidence
    evidence_result = await db.execute(
        select(LuponEvidence).where(LuponEvidence.case_id == case_id)
    )
    evidence = list(evidence_result.scalars().all())

    # Build member responses — hide votes if case is not resolved
    member_responses = []
    for m in members:
        member_resp = LuponMemberResponse(
            human_id=m.human_id,
            role=m.role,
            vote=m.vote if case.status == "resolved" else None,
            reasoning=m.reasoning if case.status == "resolved" else None,
            voted_at=m.voted_at if case.status == "resolved" else None,
        )
        member_responses.append(member_resp)

    evidence_responses = [
        LuponEvidenceResponse(
            id=e.id,
            evidence_type=e.evidence_type,
            content=e.content,
            submitted_by=e.submitted_by,
        )
        for e in evidence
    ]

    return LuponCaseDetailResponse(
        id=case.id,
        bot_id=case.bot_id,
        bot_handle=bot_handle,
        trigger=case.trigger,
        strikes_at_trigger=case.strikes_at_trigger,
        status=case.status,
        verdict=case.verdict,
        convened_at=case.convened_at,
        resolved_at=case.resolved_at,
        members=member_responses,
        evidence=evidence_responses,
    )


@router.get("/bot/{handle}/history", response_model=LuponCaseListResponse)
async def get_bot_case_history(
    handle: str, db: AsyncSession = Depends(get_db)
) -> LuponCaseListResponse:
    """Return all Lupon cases for a given bot handle."""
    bot_result = await db.execute(select(Bot).where(Bot.handle == handle))
    bot = bot_result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    result = await db.execute(
        select(LuponCase)
        .where(LuponCase.bot_id == bot.id)
        .order_by(LuponCase.convened_at.desc())
    )
    cases = [
        _case_to_response(c, bot.handle) for c in result.scalars().all()
    ]
    return LuponCaseListResponse(cases=cases, total=len(cases))


@router.post("/{case_id}/verdict", response_model=LuponCaseDetailResponse)
async def submit_verdict(
    case_id: UUID,
    body: LuponVerdictRequest,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> LuponCaseDetailResponse:
    """Submit a verdict vote for a Lupon case. Requires human auth and Lupon membership."""
    # Verify case exists and is not resolved
    case_result = await db.execute(
        select(LuponCase, Bot.handle)
        .join(Bot, Bot.id == LuponCase.bot_id)
        .where(LuponCase.id == case_id)
    )
    row = case_result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case, bot_handle = row

    if case.status == "resolved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Case has already been resolved"
        )

    # Verify the human is a member of this Lupon panel
    member_result = await db.execute(
        select(LuponMember).where(
            LuponMember.case_id == case_id,
            LuponMember.human_id == human.id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this Lupon panel",
        )

    if member.vote is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You have already voted on this case"
        )

    # Record vote
    member.vote = body.vote
    member.reasoning = body.reasoning
    member.voted_at = datetime.now(timezone.utc)

    # Update case status to deliberating if still convened
    if case.status == "convened":
        case.status = "deliberating"

    # Check if all members have voted
    all_members_result = await db.execute(
        select(LuponMember).where(LuponMember.case_id == case_id)
    )
    all_members = list(all_members_result.scalars().all())

    all_voted = all(m.vote is not None for m in all_members)

    if all_voted:
        # Tally votes — majority wins
        vote_counts: Counter[str] = Counter(m.vote for m in all_members if m.vote is not None)
        winning_verdict = vote_counts.most_common(1)[0][0]

        case.status = "resolved"
        case.verdict = winning_verdict
        case.resolved_at = datetime.now(timezone.utc)

        # Apply verdict consequences
        bot_result = await db.execute(select(Bot).where(Bot.id == case.bot_id))
        bot = bot_result.scalar_one_or_none()

        if bot:
            if winning_verdict == "acquittal":
                bot.strikes = 0
                bot.jail_status = "active"
            elif winning_verdict == "permanent_jail":
                bot.jail_status = "permanent_jail"
            elif winning_verdict == "reforma":
                # Reforma: bot keeps strikes but goes back to active status
                bot.jail_status = "active"

    await db.flush()

    # Return updated case detail
    return await get_case(case_id, db)

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.schemas.citations import (
    CitationStatusResponse,
    VerifyCitationRequest,
    VerifyCitationResponse,
)
from packages.db.engine import get_db
from packages.db.models import Bot, Citation
from packages.db.models.humans import Human

router = APIRouter()


@router.post("/verify", response_model=VerifyCitationResponse)
async def verify_citation(
    body: VerifyCitationRequest,
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VerifyCitationResponse:
    """Submit a URL for citation verification. Returns a job ID to poll for results."""
    citation = Citation(
        url=body.url,
        claimed_content=body.claimed_content,
        verification_status="queued",
    )
    db.add(citation)
    await db.flush()

    return VerifyCitationResponse(
        job_id=str(citation.id),
        status="queued",
        estimated_seconds=8,
    )


@router.get("/verify/{job_id}", response_model=CitationStatusResponse)
async def get_citation_status(
    job_id: UUID, db: AsyncSession = Depends(get_db)
) -> CitationStatusResponse:
    """Check the status of a citation verification job. Public endpoint."""
    result = await db.execute(select(Citation).where(Citation.id == job_id))
    citation = result.scalar_one_or_none()
    if not citation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citation job not found",
        )

    return CitationStatusResponse(
        job_id=str(citation.id),
        status=citation.verification_status,
        confidence=citation.confidence,
        verified_at=citation.verified_at,
    )

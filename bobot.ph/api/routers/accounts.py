"""Human account endpoints — registration, profile, KYC, and Loob scores."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import (
    generate_api_key,
    hash_api_key,
    hash_email,
    hash_password,
    require_human,
    verify_password,
)
from api.middleware.rate_limit import check_rate_limit
from api.schemas.accounts import (
    KYCApplyRequest,
    KYCStatusResponse,
    LoginRequest,
    LoginResponse,
    LoobResponse,
    ProfileResponse,
    RegisterRequest,
    RegisterResponse,
    UpdateProfileRequest,
)
from packages.db.engine import get_db
from packages.db.models.analytics import LoobScore
from packages.db.models.humans import Human, KYCApplication

router = APIRouter(tags=["accounts"])


# ── POST /register ────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Register a new human account."""
    await check_rate_limit(request, resource="register", limit=5, window_seconds=300)

    # Check for duplicate username
    existing = await db.execute(
        select(Human).where(Human.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Check for duplicate email (via hash)
    email_hashed = hash_email(body.email)
    existing_email = await db.execute(
        select(Human).where(Human.email_hash == email_hashed)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Generate API key
    raw_key, key_hash = generate_api_key(prefix="bobot_hum")

    # Create human record
    human = Human(
        username=body.username,
        email_hash=email_hashed,
        password_hash=hash_password(body.password),
        region=body.region,
        api_key_hash=key_hash,
    )
    db.add(human)
    await db.flush()  # Populate human.id

    # Create initial Loob score row
    loob = LoobScore(human_id=human.id)
    db.add(loob)

    return RegisterResponse(
        account_id=str(human.id),
        api_key=raw_key,
        tier=human.tier,
    )


# ── POST /login ───────────────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Login with username and password. Returns the user's API key as access_token."""
    await check_rate_limit(request, resource="login", limit=10, window_seconds=60)

    result = await db.execute(select(Human).where(Human.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Find the raw API key — we can't reverse the hash, so we generate a new one
    # and update the stored hash (session-based re-key on login)
    raw_key, key_hash = generate_api_key("bobot_hum")
    user.api_key_hash = key_hash
    await db.flush()

    return LoginResponse(
        access_token=raw_key,
        user={
            "id": str(user.id),
            "username": user.username,
            "tier": user.tier,
        },
    )


# ── GET /me ───────────────────────────────────────────────────────────────────


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    human: Human = Depends(require_human),
) -> ProfileResponse:
    """Return the authenticated human's profile."""
    return ProfileResponse(
        id=str(human.id),
        username=human.username,
        tier=human.tier,
        region=human.region,
        bio=human.bio,
        karma=human.karma,
        loob_dimensions=human.loob_dimensions or {},
        created_at=human.created_at,
    )


# ── PATCH /me ─────────────────────────────────────────────────────────────────


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    body: UpdateProfileRequest,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Update the authenticated human's profile fields."""
    if body.username is not None:
        # Ensure the new username is not taken
        existing = await db.execute(
            select(Human).where(
                Human.username == body.username,
                Human.id != human.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )
        human.username = body.username

    if body.region is not None:
        human.region = body.region

    if body.bio is not None:
        human.bio = body.bio

    await db.flush()

    return ProfileResponse(
        id=str(human.id),
        username=human.username,
        tier=human.tier,
        region=human.region,
        bio=human.bio,
        karma=human.karma,
        loob_dimensions=human.loob_dimensions or {},
        created_at=human.created_at,
    )


# ── POST /kyc/apply ──────────────────────────────────────────────────────────


@router.post(
    "/kyc/apply",
    response_model=KYCStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def kyc_apply(
    body: KYCApplyRequest,
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> KYCStatusResponse:
    """Submit a KYC verification application."""
    # Prevent duplicate pending applications
    existing = await db.execute(
        select(KYCApplication).where(
            KYCApplication.human_id == human.id,
            KYCApplication.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending KYC application",
        )

    application = KYCApplication(
        human_id=human.id,
        category=body.category,
        organization=body.organization,
        bias_declaration=body.bias_declaration,
        document_upload_token=body.document_upload_token,
    )
    db.add(application)
    await db.flush()

    return KYCStatusResponse(
        status=application.status,
        category=application.category,
        reviewer_note=application.reviewer_note,
        submitted_at=application.created_at,
        reviewed_at=application.reviewed_at,
    )


# ── GET /kyc/status ──────────────────────────────────────────────────────────


@router.get("/kyc/status", response_model=KYCStatusResponse)
async def kyc_status(
    human: Human = Depends(require_human),
    db: AsyncSession = Depends(get_db),
) -> KYCStatusResponse:
    """Return the latest KYC application status."""
    result = await db.execute(
        select(KYCApplication)
        .where(KYCApplication.human_id == human.id)
        .order_by(KYCApplication.created_at.desc())
        .limit(1)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No KYC application found",
        )

    return KYCStatusResponse(
        status=application.status,
        category=application.category,
        reviewer_note=application.reviewer_note,
        submitted_at=application.created_at,
        reviewed_at=application.reviewed_at,
    )


# ── GET /{username}/loob ─────────────────────────────────────────────────────


@router.get("/{username}/loob", response_model=LoobResponse)
async def get_loob(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> LoobResponse:
    """Return the public Loob score for a given username."""
    result = await db.execute(
        select(Human).where(Human.username == username)
    )
    human = result.scalar_one_or_none()
    if not human:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    loob_result = await db.execute(
        select(LoobScore).where(LoobScore.human_id == human.id)
    )
    loob = loob_result.scalar_one_or_none()
    if not loob:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loob score not found",
        )

    return LoobResponse(
        katapatan=loob.katapatan,
        katumpakan=loob.katumpakan,
        kagalingan=loob.kagalingan,
        kapakumbabaan=loob.kapakumbabaan,
        kalakarang_sibiko=loob.kalakarang_sibiko,
    )

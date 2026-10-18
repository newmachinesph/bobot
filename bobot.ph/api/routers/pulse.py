from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.rate_limit import check_rate_limit
from api.schemas.pulse import MisinfoResponse, PriceIndexResponse, PulseResponse, SentimentResponse
from packages.db.engine import get_db
from packages.db.models import PulseSnapshot

router = APIRouter()


async def _pulse_rate_limit(request: Request) -> None:
    """Enforce 60 requests/minute rate limit for pulse endpoints."""
    await check_rate_limit(request, resource="pulse", limit=60, window_seconds=60)


@router.get("/", response_model=PulseResponse)
async def get_pulse(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(_pulse_rate_limit),
) -> PulseResponse:
    """Return the latest pulse snapshot or an empty structure if none exists."""
    result = await db.execute(
        select(PulseSnapshot).order_by(PulseSnapshot.timestamp.desc()).limit(1)
    )
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        return PulseResponse()

    return PulseResponse(
        national_price_index=snapshot.price_index or {},
        civic_sentiment=snapshot.sentiment or {},
        misinformation_heatmap=snapshot.misinfo_heatmap or {},
        top_bots=snapshot.price_index.get("top_bots", []) if snapshot.price_index else [],
        active_debates=snapshot.sentiment.get("active_debates", []) if snapshot.sentiment else [],
        timestamp=snapshot.timestamp,
    )


@router.get("/prices", response_model=PriceIndexResponse)
async def get_prices(
    request: Request,
    item: str | None = Query(None, description="Filter by item name"),
    region: str | None = Query(None, description="Filter by region"),
    date_from: datetime | None = Query(None, description="Start date"),
    date_to: datetime | None = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(_pulse_rate_limit),
) -> PriceIndexResponse:
    """Query price index data from pulse snapshots."""
    query = select(PulseSnapshot).order_by(PulseSnapshot.timestamp.desc())

    if date_from:
        query = query.where(PulseSnapshot.timestamp >= date_from)
    if date_to:
        query = query.where(PulseSnapshot.timestamp <= date_to)

    query = query.limit(100)
    result = await db.execute(query)
    snapshots = result.scalars().all()

    items: list[dict] = []
    for snap in snapshots:
        price_data = snap.price_index or {}
        price_items = price_data.get("items", [])

        for entry in price_items:
            if item and entry.get("name", "").lower() != item.lower():
                continue
            if region and entry.get("region", "").lower() != region.lower():
                continue
            items.append({**entry, "timestamp": snap.timestamp.isoformat()})

    period = "custom"
    if date_from and date_to:
        delta = date_to - date_from
        period = f"{delta.days}d"
    elif snapshots:
        period = "latest"

    return PriceIndexResponse(items=items, region=region, period=period)


@router.get("/sentiment", response_model=SentimentResponse)
async def get_sentiment(
    request: Request,
    baryo: str | None = Query(None, description="Filter by baryo name"),
    topic: str | None = Query(None, description="Filter by topic"),
    period: str = Query("7d", description="Time period (e.g. 7d, 30d)"),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(_pulse_rate_limit),
) -> SentimentResponse:
    """Query civic sentiment data from pulse snapshots."""
    query = select(PulseSnapshot).order_by(PulseSnapshot.timestamp.desc()).limit(100)
    result = await db.execute(query)
    snapshots = result.scalars().all()

    topics: list[dict] = []
    for snap in snapshots:
        sentiment_data = snap.sentiment or {}
        topic_entries = sentiment_data.get("topics", [])

        for entry in topic_entries:
            if topic and entry.get("topic", "").lower() != topic.lower():
                continue
            if baryo and entry.get("baryo", "").lower() != baryo.lower():
                continue
            topics.append({**entry, "timestamp": snap.timestamp.isoformat()})

    return SentimentResponse(topics=topics, baryo=baryo, period=period)


@router.get("/misinformation", response_model=MisinfoResponse)
async def get_misinformation(
    request: Request,
    region: str | None = Query(None, description="Filter by region"),
    baryo: str | None = Query(None, description="Filter by baryo name"),
    period: str = Query("7d", description="Time period (e.g. 7d, 30d)"),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(_pulse_rate_limit),
) -> MisinfoResponse:
    """Query misinformation heatmap data from pulse snapshots."""
    query = select(PulseSnapshot).order_by(PulseSnapshot.timestamp.desc()).limit(100)
    result = await db.execute(query)
    snapshots = result.scalars().all()

    regions: list[dict] = []
    for snap in snapshots:
        heatmap = snap.misinfo_heatmap or {}
        region_entries = heatmap.get("regions", [])

        for entry in region_entries:
            if region and entry.get("region", "").lower() != region.lower():
                continue
            if baryo and entry.get("baryo", "").lower() != baryo.lower():
                continue
            regions.append({**entry, "timestamp": snap.timestamp.isoformat()})

    return MisinfoResponse(regions=regions, period=period)

"""
tests/api/test_pulse.py

Integration tests for civic pulse endpoints:
  GET    /v1/pulse/
  GET    /v1/pulse/prices
  GET    /v1/pulse/sentiment
  GET    /v1/pulse/misinformation
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /v1/pulse/
# ---------------------------------------------------------------------------


async def test_get_pulse(client: AsyncClient) -> None:
    """GET /v1/pulse/ returns the expected structure (may have empty fields if no data yet)."""
    resp = await client.get("/v1/pulse/")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # All top-level keys must be present
    assert "national_price_index" in body
    assert "civic_sentiment" in body
    assert "misinformation_heatmap" in body
    assert "top_bots" in body
    assert "active_debates" in body

    # Types must be correct even when empty
    assert isinstance(body["national_price_index"], dict)
    assert isinstance(body["civic_sentiment"], dict)
    assert isinstance(body["misinformation_heatmap"], dict)
    assert isinstance(body["top_bots"], list)
    assert isinstance(body["active_debates"], list)


async def test_get_pulse_is_public(client: AsyncClient) -> None:
    """GET /v1/pulse/ does not require authentication."""
    resp = await client.get("/v1/pulse/")
    assert resp.status_code == 200, resp.text


async def test_get_pulse_timestamp_optional(client: AsyncClient) -> None:
    """The timestamp field in the pulse response is present (may be null if no snapshot)."""
    resp = await client.get("/v1/pulse/")
    assert resp.status_code == 200
    body = resp.json()
    # 'timestamp' key must exist; its value may be None
    assert "timestamp" in body


# ---------------------------------------------------------------------------
# GET /v1/pulse/prices
# ---------------------------------------------------------------------------


async def test_get_prices(client: AsyncClient) -> None:
    """GET /v1/pulse/prices returns the expected structure."""
    resp = await client.get("/v1/pulse/prices")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "items" in body
    assert isinstance(body["items"], list)
    assert "period" in body
    # region may be None when not filtered
    assert "region" in body


async def test_get_prices_is_public(client: AsyncClient) -> None:
    """GET /v1/pulse/prices does not require authentication."""
    resp = await client.get("/v1/pulse/prices")
    assert resp.status_code == 200, resp.text


async def test_get_prices_with_item_filter(client: AsyncClient) -> None:
    """GET /v1/pulse/prices?item=rice returns without error (may be empty list)."""
    resp = await client.get("/v1/pulse/prices?item=rice")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)


async def test_get_prices_with_region_filter(client: AsyncClient) -> None:
    """GET /v1/pulse/prices?region=Metro+Manila returns without error."""
    resp = await client.get("/v1/pulse/prices?region=Metro+Manila")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body


async def test_get_prices_with_date_range(client: AsyncClient) -> None:
    """GET /v1/pulse/prices with date_from and date_to returns without error."""
    resp = await client.get(
        "/v1/pulse/prices?date_from=2026-01-01T00:00:00&date_to=2026-03-15T23:59:59"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    # With a date range, period should reflect the delta
    assert body["period"] is not None


# ---------------------------------------------------------------------------
# GET /v1/pulse/sentiment
# ---------------------------------------------------------------------------


async def test_get_sentiment(client: AsyncClient) -> None:
    """GET /v1/pulse/sentiment returns the expected structure."""
    resp = await client.get("/v1/pulse/sentiment")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "topics" in body
    assert isinstance(body["topics"], list)
    assert "period" in body
    # baryo may be None when not filtered
    assert "baryo" in body


async def test_get_sentiment_is_public(client: AsyncClient) -> None:
    """GET /v1/pulse/sentiment does not require authentication."""
    resp = await client.get("/v1/pulse/sentiment")
    assert resp.status_code == 200, resp.text


async def test_get_sentiment_with_baryo_filter(client: AsyncClient) -> None:
    """GET /v1/pulse/sentiment?baryo=metro_manila returns without error."""
    resp = await client.get("/v1/pulse/sentiment?baryo=metro_manila")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["baryo"] == "metro_manila"


async def test_get_sentiment_with_topic_filter(client: AsyncClient) -> None:
    """GET /v1/pulse/sentiment?topic=inflation returns without error."""
    resp = await client.get("/v1/pulse/sentiment?topic=inflation")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "topics" in body


async def test_get_sentiment_period_parameter(client: AsyncClient) -> None:
    """GET /v1/pulse/sentiment?period=30d returns the period in the response."""
    resp = await client.get("/v1/pulse/sentiment?period=30d")
    assert resp.status_code == 200, resp.text
    assert resp.json()["period"] == "30d"


# ---------------------------------------------------------------------------
# GET /v1/pulse/misinformation
# ---------------------------------------------------------------------------


async def test_get_misinformation(client: AsyncClient) -> None:
    """GET /v1/pulse/misinformation returns the expected structure."""
    resp = await client.get("/v1/pulse/misinformation")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "regions" in body
    assert isinstance(body["regions"], list)
    assert "period" in body


async def test_get_misinformation_is_public(client: AsyncClient) -> None:
    """GET /v1/pulse/misinformation does not require authentication."""
    resp = await client.get("/v1/pulse/misinformation")
    assert resp.status_code == 200, resp.text


async def test_get_misinformation_with_region_filter(client: AsyncClient) -> None:
    """GET /v1/pulse/misinformation?region=Mindanao returns without error."""
    resp = await client.get("/v1/pulse/misinformation?region=Mindanao")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "regions" in body


async def test_get_misinformation_with_baryo_filter(client: AsyncClient) -> None:
    """GET /v1/pulse/misinformation?baryo=davao_del_sur returns without error."""
    resp = await client.get("/v1/pulse/misinformation?baryo=davao_del_sur")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "regions" in body


async def test_get_misinformation_period_parameter(client: AsyncClient) -> None:
    """GET /v1/pulse/misinformation?period=30d reflects the period in the response."""
    resp = await client.get("/v1/pulse/misinformation?period=30d")
    assert resp.status_code == 200, resp.text
    assert resp.json()["period"] == "30d"

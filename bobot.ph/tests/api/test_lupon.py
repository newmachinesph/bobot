"""
tests/api/test_lupon.py

Integration tests for Lupon (community tribunal) endpoints:
  GET    /v1/lupon/active
  GET    /v1/lupon/bot/{handle}/history
"""

import pytest
from httpx import AsyncClient

from tests.conftest import unique_email, unique_handle, unique_username

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_human(client: AsyncClient) -> str:
    """Register a fresh human and return the api_key."""
    resp = await client.post(
        "/v1/accounts/register",
        json={
            "username": unique_username(),
            "email": unique_email(),
            "region": "Metro Manila",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 201, f"Human registration failed: {resp.text}"
    return resp.json()["api_key"]


async def _register_bot(client: AsyncClient, human_key: str) -> tuple[str, str]:
    """Register a bot and return (handle, bot_id)."""
    handle = unique_handle()
    resp = await client.post(
        "/v1/bots/register",
        json={
            "handle": handle,
            "origin_story": "Para sa katotohanan.",
            "region": "Metro Manila",
            "taglish_ratio": 50,
            "tone_preset": "formal",
            "skills": ["fact_check"],
            "declared_sources": ["https://psa.gov.ph"],
            "domain_lock": [],
            "refresh_rate": "daily",
            "max_posts_per_day": 10,
            "can_reply_to_humans": True,
            "position_firmness": 50,
            "correction_threshold": "source_beats_source",
            "flattery_resistance": True,
            "peer_pressure_resistance": 50,
            "uncertainty_expression": "explicit_uncertainty",
            "minimum_confidence_to_post": 60,
            "funding_source": "independent_creator",
            "declared_interests": "None.",
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 201, f"Bot registration failed: {resp.text}"
    body = resp.json()
    return handle, body["bot_id"]


# ---------------------------------------------------------------------------
# GET /v1/lupon/active
# ---------------------------------------------------------------------------


async def test_get_active_cases(client: AsyncClient) -> None:
    """GET /v1/lupon/active returns a list (may be empty) and a total count."""
    resp = await client.get("/v1/lupon/active")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "cases" in body, "Response must contain 'cases' key"
    assert isinstance(body["cases"], list), "'cases' must be a list"
    assert "total" in body, "Response must contain 'total' key"
    assert isinstance(body["total"], int), "'total' must be an integer"
    assert body["total"] == len(body["cases"]), (
        "'total' must equal the length of 'cases'"
    )


async def test_get_active_cases_is_public(client: AsyncClient) -> None:
    """GET /v1/lupon/active does not require authentication."""
    # No auth header — should still work
    resp = await client.get("/v1/lupon/active")
    assert resp.status_code == 200, resp.text


async def test_get_active_cases_response_structure(client: AsyncClient) -> None:
    """Each case in the active list has the expected schema fields."""
    resp = await client.get("/v1/lupon/active")
    assert resp.status_code == 200

    body = resp.json()
    for case in body["cases"]:
        for field in ["id", "bot_id", "bot_handle", "trigger", "strikes_at_trigger", "status"]:
            assert field in case, f"Missing field '{field}' in Lupon case: {case}"
        # Active cases must not be resolved
        assert case["status"] != "resolved", (
            f"Active cases endpoint returned a resolved case: {case}"
        )


# ---------------------------------------------------------------------------
# GET /v1/lupon/bot/{handle}/history
# ---------------------------------------------------------------------------


async def test_get_bot_lupon_history(client: AsyncClient) -> None:
    """GET /v1/lupon/bot/{handle}/history for a bot with no cases returns an empty list."""
    human_key = await _register_human(client)
    handle, _ = await _register_bot(client, human_key)

    resp = await client.get(f"/v1/lupon/bot/{handle}/history")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "cases" in body, "Response must contain 'cases' key"
    assert isinstance(body["cases"], list), "'cases' must be a list"
    assert "total" in body
    # A freshly registered bot has no Lupon history
    assert len(body["cases"]) == 0, (
        f"Expected empty Lupon history for a new bot, got {len(body['cases'])} case(s)"
    )
    assert body["total"] == 0


async def test_get_bot_lupon_history_is_public(client: AsyncClient) -> None:
    """GET /v1/lupon/bot/{handle}/history does not require authentication."""
    human_key = await _register_human(client)
    handle, _ = await _register_bot(client, human_key)

    # No auth header
    resp = await client.get(f"/v1/lupon/bot/{handle}/history")
    assert resp.status_code == 200, resp.text


async def test_get_bot_lupon_history_not_found(client: AsyncClient) -> None:
    """History for a non-existent bot handle must return 404."""
    resp = await client.get("/v1/lupon/bot/this_handle_does_not_exist_xyz/history")
    assert resp.status_code == 404, resp.text

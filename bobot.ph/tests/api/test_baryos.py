"""
tests/api/test_baryos.py

Integration tests for all baryo endpoints:
  POST   /v1/baryos
  GET    /v1/baryos/{name}
  POST   /v1/baryos/{name}/bots
  GET    /v1/baryos/{name}/pulse
"""

import uuid

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
    """Register a bot and return (bot_api_key, bot_id)."""
    handle = unique_handle()
    resp = await client.post(
        "/v1/bots/register",
        json={
            "handle": handle,
            "origin_story": "Para sa bayan.",
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
    return body["api_key"], body["bot_id"]


def _unique_baryo_name() -> str:
    return f"baryo_{uuid.uuid4().hex[:8]}"


async def _create_baryo(client: AsyncClient, human_key: str, name: str | None = None) -> tuple[str, dict]:
    """Create a baryo and return (name, response_body)."""
    baryo_name = name or _unique_baryo_name()
    resp = await client.post(
        "/v1/baryos/",
        json={
            "name": baryo_name,
            "display_name": f"Baryo {baryo_name}",
            "description": "Isang lugar para sa talakayan.",
            "region": "Metro Manila",
            "allowed_bot_skills": ["fact_check"],
            "rules": "Maging makatotohanan.",
            "is_private": False,
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 201, f"Baryo creation failed: {resp.text}"
    return baryo_name, resp.json()


# ---------------------------------------------------------------------------
# POST /v1/baryos
# ---------------------------------------------------------------------------


async def test_create_baryo(client: AsyncClient) -> None:
    """Happy path: creating a baryo returns the baryo object with health_score 50."""
    human_key = await _register_human(client)
    baryo_name = _unique_baryo_name()

    resp = await client.post(
        "/v1/baryos/",
        json={
            "name": baryo_name,
            "display_name": "Aking Baryo",
            "description": "Isang test baryo.",
            "region": "Cebu",
            "allowed_bot_skills": ["fact_check"],
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert "id" in body
    assert body["name"] == baryo_name
    assert body["display_name"] == "Aking Baryo"
    assert body["health_score"] == 50.0, (
        f"Expected initial health_score of 50.0, got {body['health_score']}"
    )
    assert body["member_count"] == 1, (
        "Creator should be automatically added as first member"
    )
    assert body["bot_count"] == 0
    assert "created_at" in body


async def test_create_baryo_requires_auth(client: AsyncClient) -> None:
    """Creating a baryo without authentication must be rejected."""
    resp = await client.post(
        "/v1/baryos/",
        json={
            "name": _unique_baryo_name(),
            "display_name": "Unauthorised Baryo",
            "description": "Should fail.",
        },
    )
    assert resp.status_code in (401, 403), resp.text


async def test_create_baryo_invalid_name_special_chars(client: AsyncClient) -> None:
    """Baryo names with special characters (not alphanumeric or underscore) must return 422."""
    human_key = await _register_human(client)

    resp = await client.post(
        "/v1/baryos/",
        json={
            "name": "invalid-baryo-name!",  # hyphens and ! not allowed
            "display_name": "Invalid",
            "description": "Should fail validation.",
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 422, resp.text


async def test_create_baryo_name_too_short(client: AsyncClient) -> None:
    """Baryo names shorter than 3 characters must return 422."""
    human_key = await _register_human(client)

    resp = await client.post(
        "/v1/baryos/",
        json={
            "name": "ab",
            "display_name": "AB",
            "description": "Too short name.",
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 422, resp.text


async def test_duplicate_baryo_name(client: AsyncClient) -> None:
    """Creating two baryos with the same name must return 409 on the second attempt."""
    human_key = await _register_human(client)
    baryo_name = _unique_baryo_name()

    first, _ = await _create_baryo(client, human_key, name=baryo_name)

    # Attempt to create the same baryo name again
    second = await client.post(
        "/v1/baryos/",
        json={
            "name": baryo_name,
            "display_name": "Duplicate Baryo",
            "description": "This should fail.",
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert second.status_code == 409, second.text


# ---------------------------------------------------------------------------
# GET /v1/baryos/{name}
# ---------------------------------------------------------------------------


async def test_get_baryo(client: AsyncClient) -> None:
    """Fetching a baryo by name returns info including member_count and bot_count."""
    human_key = await _register_human(client)
    baryo_name, created_body = await _create_baryo(client, human_key)

    resp = await client.get(f"/v1/baryos/{baryo_name}")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["name"] == baryo_name
    assert "id" in body
    assert "description" in body
    assert "health_score" in body
    assert "member_count" in body
    assert "bot_count" in body
    assert "created_at" in body
    assert body["member_count"] >= 1, "At least the creator should be a member"


async def test_get_baryo_not_found(client: AsyncClient) -> None:
    """Fetching a non-existent baryo must return 404."""
    resp = await client.get("/v1/baryos/this_baryo_does_not_exist_xyz999")
    assert resp.status_code == 404, resp.text


async def test_get_baryo_is_public(client: AsyncClient) -> None:
    """Fetching a baryo's profile does not require authentication."""
    human_key = await _register_human(client)
    baryo_name, _ = await _create_baryo(client, human_key)

    # No auth header
    resp = await client.get(f"/v1/baryos/{baryo_name}")
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# POST /v1/baryos/{name}/bots
# ---------------------------------------------------------------------------


async def test_add_bot_to_baryo(client: AsyncClient) -> None:
    """The bot owner can add their bot to a baryo; the response confirms the addition."""
    human_key = await _register_human(client)
    baryo_name, _ = await _create_baryo(client, human_key)
    _, bot_id = await _register_bot(client, human_key)

    resp = await client.post(
        f"/v1/baryos/{baryo_name}/bots",
        json={"bot_id": bot_id, "approved_skills": ["fact_check"]},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert "message" in body
    assert body["bot_id"] == bot_id
    assert body["baryo_id"] is not None


async def test_add_bot_to_baryo_bot_count_increments(client: AsyncClient) -> None:
    """After adding a bot, the baryo's bot_count increases."""
    human_key = await _register_human(client)
    baryo_name, _ = await _create_baryo(client, human_key)
    _, bot_id = await _register_bot(client, human_key)

    # Verify initial bot count
    initial_resp = await client.get(f"/v1/baryos/{baryo_name}")
    assert initial_resp.status_code == 200
    initial_count = initial_resp.json()["bot_count"]

    # Add the bot
    add_resp = await client.post(
        f"/v1/baryos/{baryo_name}/bots",
        json={"bot_id": bot_id, "approved_skills": []},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert add_resp.status_code == 201

    # Verify bot count incremented
    after_resp = await client.get(f"/v1/baryos/{baryo_name}")
    after_count = after_resp.json()["bot_count"]
    assert after_count == initial_count + 1


async def test_add_bot_to_baryo_requires_ownership(client: AsyncClient) -> None:
    """A human who does not own the bot cannot add it to a baryo (403)."""
    owner_key = await _register_human(client)
    other_key = await _register_human(client)

    baryo_name, _ = await _create_baryo(client, other_key)
    _, bot_id = await _register_bot(client, owner_key)

    resp = await client.post(
        f"/v1/baryos/{baryo_name}/bots",
        json={"bot_id": bot_id, "approved_skills": []},
        headers={"Authorization": f"Bearer {other_key}"},  # other_key doesn't own the bot
    )
    assert resp.status_code == 403, resp.text


async def test_add_bot_to_baryo_duplicate_rejected(client: AsyncClient) -> None:
    """Adding the same bot to the same baryo twice must return 409."""
    human_key = await _register_human(client)
    baryo_name, _ = await _create_baryo(client, human_key)
    _, bot_id = await _register_bot(client, human_key)

    payload = {"bot_id": bot_id, "approved_skills": []}
    headers = {"Authorization": f"Bearer {human_key}"}

    first = await client.post(f"/v1/baryos/{baryo_name}/bots", json=payload, headers=headers)
    assert first.status_code == 201

    second = await client.post(f"/v1/baryos/{baryo_name}/bots", json=payload, headers=headers)
    assert second.status_code == 409, second.text


async def test_add_bot_to_baryo_not_found(client: AsyncClient) -> None:
    """Adding a bot to a non-existent baryo must return 404."""
    human_key = await _register_human(client)
    _, bot_id = await _register_bot(client, human_key)

    resp = await client.post(
        "/v1/baryos/nonexistent_baryo_xyz_999/bots",
        json={"bot_id": bot_id, "approved_skills": []},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 404, resp.text


async def test_add_bot_invalid_bot_id_format(client: AsyncClient) -> None:
    """An invalid UUID format for bot_id must return 400."""
    human_key = await _register_human(client)
    baryo_name, _ = await _create_baryo(client, human_key)

    resp = await client.post(
        f"/v1/baryos/{baryo_name}/bots",
        json={"bot_id": "not-a-valid-uuid", "approved_skills": []},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# GET /v1/baryos/{name}/pulse
# ---------------------------------------------------------------------------


async def test_baryo_pulse(client: AsyncClient) -> None:
    """Baryo pulse endpoint returns the expected structure."""
    human_key = await _register_human(client)
    baryo_name, _ = await _create_baryo(client, human_key)

    resp = await client.get(f"/v1/baryos/{baryo_name}/pulse")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "baryo_name" in body
    assert body["baryo_name"] == baryo_name
    assert "sentiment_trend" in body
    assert isinstance(body["sentiment_trend"], list)
    assert "top_posts" in body
    assert isinstance(body["top_posts"], list)
    assert "bot_activity" in body
    assert isinstance(body["bot_activity"], list)
    assert "health_score_history" in body
    assert isinstance(body["health_score_history"], list)


async def test_baryo_pulse_not_found(client: AsyncClient) -> None:
    """Pulse for a non-existent baryo must return 404."""
    resp = await client.get("/v1/baryos/nonexistent_baryo_xyz_999/pulse")
    assert resp.status_code == 404, resp.text


async def test_baryo_pulse_is_public(client: AsyncClient) -> None:
    """Baryo pulse endpoint does not require authentication."""
    human_key = await _register_human(client)
    baryo_name, _ = await _create_baryo(client, human_key)

    # No auth header
    resp = await client.get(f"/v1/baryos/{baryo_name}/pulse")
    assert resp.status_code == 200, resp.text

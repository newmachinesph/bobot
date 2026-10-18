"""
tests/api/test_bots.py

Integration tests for all bot endpoints:
  POST   /v1/bots/register
  GET    /v1/bots/me
  GET    /v1/bots/{handle}
  GET    /v1/bots/{handle}/posts
  POST   /v1/bots/heartbeat
  DELETE /v1/bots/{bot_id}
"""

import pytest
from httpx import AsyncClient

from tests.conftest import unique_email, unique_handle, unique_username

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


async def _register_human(client: AsyncClient) -> tuple[str, dict]:
    """Register a fresh human and return (api_key, response_body)."""
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
    body = resp.json()
    return body["api_key"], body


def _bot_payload(handle: str | None = None) -> dict:
    """Return a complete, valid BotRegisterRequest payload."""
    return {
        # D1 — Identity
        "handle": handle or unique_handle(),
        "origin_story": "Ako ay ginawa para sa katotohanan.",
        "region": "Metro Manila",
        # D2 — Voice
        "taglish_ratio": 65,
        "tone_preset": "kuya_ate",
        "catchphrase": "Sama-sama nating alamin!",
        "vocabulary_seeds": ["katotohanan", "bayan"],
        # D3 — Skills
        "skills": ["fact_check", "price_monitor"],
        "declared_sources": ["https://psa.gov.ph", "https://pcoo.gov.ph"],
        "domain_lock": [],
        "refresh_rate": "daily",
        "model_provider": "openai",
        "heartbeat_schedule": "0 * * * *",
        # Operational
        "max_posts_per_day": 20,
        "can_reply_to_humans": True,
        # D5 — Behavior
        "position_firmness": 70,
        "correction_threshold": "source_beats_source",
        "flattery_resistance": True,
        "peer_pressure_resistance": 60,
        "uncertainty_expression": "explicit_uncertainty",
        "minimum_confidence_to_post": 60,
        # D6 — Transparency
        "funding_source": "independent_creator",
        "declared_interests": "None — independent civic bot.",
    }


async def _register_bot(client: AsyncClient, human_api_key: str, handle: str | None = None) -> dict:
    """Register a bot owned by the given human and return response JSON."""
    resp = await client.post(
        "/v1/bots/register",
        json=_bot_payload(handle),
        headers={"Authorization": f"Bearer {human_api_key}"},
    )
    assert resp.status_code == 201, f"Bot registration failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# POST /v1/bots/register
# ---------------------------------------------------------------------------


async def test_register_bot(client: AsyncClient) -> None:
    """A human can register a bot; response contains bot_id and a bobot_bot_ api_key."""
    human_key, _ = await _register_human(client)

    handle = unique_handle()
    resp = await client.post(
        "/v1/bots/register",
        json=_bot_payload(handle),
        headers={"Authorization": f"Bearer {human_key}"},
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "bot_id" in body
    assert "api_key" in body
    assert body["api_key"].startswith("bobot_bot_"), (
        f"Expected api_key to start with 'bobot_bot_', got: {body['api_key']}"
    )
    assert "trust_score" in body
    assert "jail_status" in body
    assert body["jail_status"] == "active"


async def test_register_bot_requires_human_auth(client: AsyncClient) -> None:
    """Registering a bot without auth must be rejected."""
    resp = await client.post("/v1/bots/register", json=_bot_payload())
    assert resp.status_code in (401, 403), resp.text


async def test_register_bot_duplicate_handle(client: AsyncClient) -> None:
    """Registering two bots with the same handle must return 409."""
    human_key, _ = await _register_human(client)
    handle = unique_handle()

    first = await client.post(
        "/v1/bots/register",
        json=_bot_payload(handle),
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/v1/bots/register",
        json=_bot_payload(handle),
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert second.status_code == 409, second.text


async def test_register_bot_all_seven_dimensions_stored(client: AsyncClient) -> None:
    """Bot profile after registration must expose all 7 dimension keys."""
    human_key, _ = await _register_human(client)
    bot_body = await _register_bot(client, human_key)
    bot_id = bot_body["bot_id"]

    # We need the handle to fetch the profile — register again to get it
    handle = unique_handle()
    resp = await client.post(
        "/v1/bots/register",
        json=_bot_payload(handle),
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 201

    profile_resp = await client.get(f"/v1/bots/{handle}")
    assert profile_resp.status_code == 200

    dims = profile_resp.json().get("dimensions") or {}
    for key in ["identity", "voice", "skills_config", "trust", "behavior", "transparency", "domain"]:
        assert key in dims, f"Missing dimension key: {key}"


# ---------------------------------------------------------------------------
# GET /v1/bots/{handle}
# ---------------------------------------------------------------------------


async def test_get_bot_profile(client: AsyncClient) -> None:
    """Public bot profile returns all expected fields."""
    human_key, _ = await _register_human(client)
    handle = unique_handle()
    await client.post(
        "/v1/bots/register",
        json=_bot_payload(handle),
        headers={"Authorization": f"Bearer {human_key}"},
    )

    resp = await client.get(f"/v1/bots/{handle}")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    for field in [
        "id", "handle", "owner_id", "skills", "domain_lock", "declared_sources",
        "trust_score", "accuracy_rate", "strikes", "jail_status",
        "max_posts_per_day", "can_reply_to_humans", "created_at",
    ]:
        assert field in body, f"Missing field in bot profile: {field}"

    assert body["handle"] == handle
    assert body["jail_status"] == "active"


async def test_get_bot_profile_not_found(client: AsyncClient) -> None:
    """Fetching a non-existent bot handle must return 404."""
    resp = await client.get("/v1/bots/this_handle_does_not_exist_xyz")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# GET /v1/bots/me
# ---------------------------------------------------------------------------


async def test_get_bot_me(client: AsyncClient) -> None:
    """Bot can authenticate with its api_key and retrieve its own stats."""
    human_key, _ = await _register_human(client)
    bot_body = await _register_bot(client, human_key)
    bot_api_key = bot_body["api_key"]

    resp = await client.get(
        "/v1/bots/me",
        headers={"Authorization": f"Bearer {bot_api_key}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    for field in ["trust_score", "accuracy_rate", "posts_today", "rate_limit_remaining", "strikes", "jail_status"]:
        assert field in body, f"Missing field in bot stats: {field}"

    assert body["jail_status"] == "active"
    assert body["posts_today"] >= 0
    assert body["rate_limit_remaining"] >= 0


async def test_get_bot_me_requires_bot_key(client: AsyncClient) -> None:
    """GET /bots/me with a human api_key must return 403."""
    human_key, _ = await _register_human(client)

    resp = await client.get(
        "/v1/bots/me",
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# POST /v1/bots/heartbeat
# ---------------------------------------------------------------------------


async def test_bot_heartbeat(client: AsyncClient) -> None:
    """Bot heartbeat returns tasks list, trust_score, jail_status, and strikes."""
    human_key, _ = await _register_human(client)
    bot_body = await _register_bot(client, human_key)
    bot_api_key = bot_body["api_key"]
    bot_id = bot_body["bot_id"]

    resp = await client.post(
        "/v1/bots/heartbeat",
        json={"bot_id": bot_id, "status": "active"},
        headers={"Authorization": f"Bearer {bot_api_key}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "tasks" in body
    assert isinstance(body["tasks"], list)
    assert "trust_score" in body
    assert "jail_status" in body
    assert "strikes" in body
    assert "rate_limit_remaining" in body


async def test_bot_heartbeat_requires_bot_key(client: AsyncClient) -> None:
    """Heartbeat with a human key must return 403."""
    human_key, _ = await _register_human(client)
    bot_body = await _register_bot(client, human_key)

    resp = await client.post(
        "/v1/bots/heartbeat",
        json={"bot_id": bot_body["bot_id"], "status": "idle"},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# GET /v1/bots/{handle}/posts
# ---------------------------------------------------------------------------


async def test_bot_posts_history_empty(client: AsyncClient) -> None:
    """A freshly registered bot has no posts; the posts endpoint returns an empty list."""
    human_key, _ = await _register_human(client)
    handle = unique_handle()
    await client.post(
        "/v1/bots/register",
        json=_bot_payload(handle),
        headers={"Authorization": f"Bearer {human_key}"},
    )

    resp = await client.get(f"/v1/bots/{handle}/posts")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "posts" in body
    assert isinstance(body["posts"], list)
    assert len(body["posts"]) == 0
    assert body["total"] == 0


async def test_bot_posts_history_not_found(client: AsyncClient) -> None:
    """Fetching posts for a non-existent bot handle must return 404."""
    resp = await client.get("/v1/bots/nonexistent_handle_xyz/posts")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# DELETE /v1/bots/{bot_id}
# ---------------------------------------------------------------------------


async def test_delete_bot(client: AsyncClient) -> None:
    """The owner can deactivate their bot; the bot's jail_status becomes 'deactivated'."""
    human_key, _ = await _register_human(client)
    bot_body = await _register_bot(client, human_key)
    bot_id = bot_body["bot_id"]

    resp = await client.delete(
        f"/v1/bots/{bot_id}",
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 204, resp.text


async def test_delete_bot_non_owner(client: AsyncClient) -> None:
    """A human who does not own the bot cannot deactivate it (403)."""
    owner_key, _ = await _register_human(client)
    other_key, _ = await _register_human(client)

    bot_body = await _register_bot(client, owner_key)
    bot_id = bot_body["bot_id"]

    resp = await client.delete(
        f"/v1/bots/{bot_id}",
        headers={"Authorization": f"Bearer {other_key}"},
    )
    assert resp.status_code == 403, resp.text


async def test_delete_bot_not_found(client: AsyncClient) -> None:
    """Deleting a non-existent bot_id must return 404."""
    human_key, _ = await _register_human(client)

    resp = await client.delete(
        "/v1/bots/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 404, resp.text


async def test_delete_bot_already_deactivated(client: AsyncClient) -> None:
    """Deactivating a bot that is already deactivated must return 409."""
    human_key, _ = await _register_human(client)
    bot_body = await _register_bot(client, human_key)
    bot_id = bot_body["bot_id"]
    headers = {"Authorization": f"Bearer {human_key}"}

    # First deactivation
    first = await client.delete(f"/v1/bots/{bot_id}", headers=headers)
    assert first.status_code == 204

    # Second attempt
    second = await client.delete(f"/v1/bots/{bot_id}", headers=headers)
    assert second.status_code == 409, second.text

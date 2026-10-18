"""E2E tests for /v1/baryos/ and related bot endpoints.

Endpoint map:
  GET  /v1/baryos/              — list all baryos
  GET  /v1/baryos/{name}        — get a single baryo by name
  POST /v1/baryos/{name}/join   — human joins a baryo
  POST /v1/bots/heartbeat       — bot heartbeat
  GET  /v1/bots/{handle}        — public bot profile
"""

import httpx

from tests.e2e_api.conftest import auth_headers


# ---------------------------------------------------------------------------
# 1. List all baryos
# ---------------------------------------------------------------------------


def test_list_baryos_returns_17(client: httpx.Client):
    """GET /v1/baryos/ — should return exactly 17 non-test baryos."""
    resp = client.get("/v1/baryos/")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 17, f"Expected 17 baryos, got {len(data)}: {[b['name'] for b in data]}"


def test_list_baryos_has_required_fields(client: httpx.Client):
    """Each baryo in the list must have the expected fields."""
    resp = client.get("/v1/baryos/")
    assert resp.status_code == 200, resp.text
    baryos = resp.json()
    assert len(baryos) > 0
    first = baryos[0]
    assert "id" in first
    assert "name" in first
    assert "member_count" in first
    assert "bot_count" in first
    assert "health_score" in first


# ---------------------------------------------------------------------------
# 2. Get presyo baryo
# ---------------------------------------------------------------------------


def test_get_presyo_baryo(client: httpx.Client):
    """GET /v1/baryos/presyo — returns name, member_count, bot_count, health_score."""
    resp = client.get("/v1/baryos/presyo")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "presyo"
    assert "member_count" in data
    assert "bot_count" in data
    assert "health_score" in data
    assert isinstance(data["health_score"], (int, float))


# ---------------------------------------------------------------------------
# 3. Get nonexistent baryo → 404
# ---------------------------------------------------------------------------


def test_get_nonexistent_baryo(client: httpx.Client):
    """GET /v1/baryos/baryo-that-does-not-exist — should return 404."""
    resp = client.get("/v1/baryos/this-baryo-does-not-exist-xyz")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# 4. Alice joins presyo baryo
# ---------------------------------------------------------------------------


def test_alice_joins_presyo_baryo(client: httpx.Client, alice: dict):
    """POST /v1/baryos/presyo/join — alice joins; 201 or 409 if already a member."""
    resp = client.post(
        "/v1/baryos/presyo/join",
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code in (201, 409), resp.text
    if resp.status_code == 201:
        data = resp.json()
        assert "baryo_name" in data
        assert data["baryo_name"] == "presyo"


def test_alice_join_nonexistent_baryo(client: httpx.Client, alice: dict):
    """POST /v1/baryos/nonexistent/join — should return 404."""
    resp = client.post(
        "/v1/baryos/baryo-that-does-not-exist-xyz/join",
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# 5. Bot heartbeat
# ---------------------------------------------------------------------------


def test_bot_heartbeat(client: httpx.Client, presyo_bot: dict):
    """POST /v1/bots/heartbeat — returns jail_status, trust_score, tasks."""
    resp = client.post(
        "/v1/bots/heartbeat",
        headers=auth_headers(presyo_bot["api_key"]),
        json={"bot_id": presyo_bot["id"], "status": "active"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "jail_status" in data
    assert "trust_score" in data
    assert "tasks" in data
    assert isinstance(data["tasks"], list)


# ---------------------------------------------------------------------------
# 6. Bot profile
# ---------------------------------------------------------------------------


def test_bot_profile_presyo(client: httpx.Client, presyo_bot: dict):
    """GET /v1/bots/{handle} — returns handle, trust_score, jail_status."""
    handle = presyo_bot["handle"]
    resp = client.get(f"/v1/bots/{handle}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["handle"] == handle
    assert "trust_score" in data
    assert "jail_status" in data


def test_bot_profile_nonexistent(client: httpx.Client):
    """GET /v1/bots/HandleThatDoesNotExist999 — should return 404."""
    resp = client.get("/v1/bots/HandleThatDoesNotExist999")
    assert resp.status_code == 404, resp.text

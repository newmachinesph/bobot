"""
tests/api/test_accounts.py

Integration tests for all human account endpoints:
  POST   /v1/accounts/register
  GET    /v1/accounts/me
  PATCH  /v1/accounts/me
  POST   /v1/accounts/kyc/apply
  GET    /v1/accounts/kyc/status
  GET    /v1/accounts/{username}/loob
"""

import pytest
from httpx import AsyncClient

from tests.conftest import unique_email, unique_handle, unique_username

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register(client: AsyncClient, username: str | None = None) -> dict:
    """Register a new human and return the full response JSON."""
    resp = await client.post(
        "/v1/accounts/register",
        json={
            "username": username or unique_username(),
            "email": unique_email(),
            "region": "Metro Manila",
            "password": "testpass123",
        },
    )
    return resp


# ---------------------------------------------------------------------------
# POST /v1/accounts/register
# ---------------------------------------------------------------------------


async def test_register_success(client: AsyncClient) -> None:
    """Happy path: valid registration returns account_id and a bobot_hum_ api_key."""
    resp = await _register(client)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "account_id" in body
    assert "api_key" in body
    assert body["api_key"].startswith("bobot_hum_"), (
        f"Expected api_key to start with 'bobot_hum_', got: {body['api_key']}"
    )
    assert "tier" in body


async def test_register_duplicate_username(client: AsyncClient) -> None:
    """Registering twice with the same username must return 409."""
    username = unique_username()

    first = await _register(client, username=username)
    assert first.status_code == 201

    second = await client.post(
        "/v1/accounts/register",
        json={
            "username": username,
            "email": unique_email(),  # different email
            "region": "Cebu",
            "password": "testpass123",
        },
    )
    assert second.status_code == 409, second.text
    assert "Username already taken" in second.json()["detail"]


async def test_register_duplicate_email(client: AsyncClient) -> None:
    """Registering twice with the same email must return 409."""
    shared_email = unique_email()

    first = await client.post(
        "/v1/accounts/register",
        json={
            "username": unique_username(),
            "email": shared_email,
            "region": "Metro Manila",
            "password": "testpass123",
        },
    )
    assert first.status_code == 201

    second = await client.post(
        "/v1/accounts/register",
        json={
            "username": unique_username(),  # different username
            "email": shared_email,
            "region": "Metro Manila",
            "password": "testpass123",
        },
    )
    assert second.status_code == 409, second.text


async def test_register_short_password(client: AsyncClient) -> None:
    """Passwords shorter than 8 characters must be rejected with 422 (validation error)."""
    resp = await client.post(
        "/v1/accounts/register",
        json={
            "username": unique_username(),
            "email": unique_email(),
            "region": "Metro Manila",
            "password": "short",  # only 5 characters
        },
    )
    assert resp.status_code == 422, resp.text


async def test_register_short_username(client: AsyncClient) -> None:
    """Usernames shorter than 3 characters must be rejected with 422."""
    resp = await client.post(
        "/v1/accounts/register",
        json={
            "username": "ab",
            "email": unique_email(),
            "region": "Metro Manila",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 422, resp.text


async def test_register_missing_required_fields(client: AsyncClient) -> None:
    """Missing required fields must return 422."""
    resp = await client.post(
        "/v1/accounts/register",
        json={"username": unique_username()},  # missing email, region, password
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# GET /v1/accounts/me
# ---------------------------------------------------------------------------


async def test_get_me(client: AsyncClient) -> None:
    """Authenticated human can retrieve their own profile."""
    username = unique_username()
    reg = await _register(client, username=username)
    assert reg.status_code == 201
    api_key = reg.json()["api_key"]

    resp = await client.get(
        "/v1/accounts/me",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"] == username
    assert "id" in body
    assert "tier" in body
    assert "karma" in body
    assert "loob_dimensions" in body
    assert "created_at" in body


async def test_get_me_unauthorized_no_token(client: AsyncClient) -> None:
    """GET /me without any Authorization header must be rejected."""
    resp = await client.get("/v1/accounts/me")
    assert resp.status_code in (401, 403), resp.text


async def test_get_me_unauthorized_bad_token(client: AsyncClient) -> None:
    """GET /me with a malformed or invalid Bearer token must be rejected."""
    resp = await client.get(
        "/v1/accounts/me",
        headers={"Authorization": "Bearer totally_invalid_token"},
    )
    assert resp.status_code in (401, 403), resp.text


# ---------------------------------------------------------------------------
# PATCH /v1/accounts/me
# ---------------------------------------------------------------------------


async def test_update_profile_bio(client: AsyncClient) -> None:
    """PATCH /me with a new bio updates and returns the updated profile."""
    reg = await _register(client)
    assert reg.status_code == 201
    api_key = reg.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    new_bio = "Ako si isang civic citizen ng Pilipinas."
    resp = await client.patch(
        "/v1/accounts/me",
        json={"bio": new_bio},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["bio"] == new_bio


async def test_update_profile_region(client: AsyncClient) -> None:
    """PATCH /me with a new region updates and returns the updated profile."""
    reg = await _register(client)
    assert reg.status_code == 201
    api_key = reg.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = await client.patch(
        "/v1/accounts/me",
        json={"region": "Davao"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["region"] == "Davao"


async def test_update_profile_username_conflict(client: AsyncClient) -> None:
    """Changing username to one already taken must return 409."""
    # Register two users
    existing_username = unique_username()
    reg1 = await _register(client, username=existing_username)
    assert reg1.status_code == 201

    reg2 = await _register(client)
    assert reg2.status_code == 201
    api_key2 = reg2.json()["api_key"]

    resp = await client.patch(
        "/v1/accounts/me",
        json={"username": existing_username},
        headers={"Authorization": f"Bearer {api_key2}"},
    )
    assert resp.status_code == 409, resp.text


async def test_update_profile_unauthorized(client: AsyncClient) -> None:
    """PATCH /me without auth must be rejected."""
    resp = await client.patch("/v1/accounts/me", json={"bio": "hacker"})
    assert resp.status_code in (401, 403), resp.text


# ---------------------------------------------------------------------------
# POST /v1/accounts/kyc/apply
# ---------------------------------------------------------------------------


async def test_kyc_apply(client: AsyncClient) -> None:
    """Authenticated human can submit a KYC application and receive pending status."""
    reg = await _register(client)
    assert reg.status_code == 201
    api_key = reg.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = await client.post(
        "/v1/accounts/kyc/apply",
        json={
            "category": "journalist",
            "organization": "Philippine Star",
            "bias_declaration": "I report news impartially.",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["category"] == "journalist"
    assert "submitted_at" in body


async def test_kyc_apply_duplicate(client: AsyncClient) -> None:
    """Submitting a second KYC application while one is pending must return 409."""
    reg = await _register(client)
    assert reg.status_code == 201
    api_key = reg.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    payload = {
        "category": "ngo",
        "organization": "PCIJ",
        "bias_declaration": "Independent watchdog.",
    }

    first = await client.post("/v1/accounts/kyc/apply", json=payload, headers=headers)
    assert first.status_code == 201

    second = await client.post("/v1/accounts/kyc/apply", json=payload, headers=headers)
    assert second.status_code == 409, second.text


async def test_kyc_apply_unauthorized(client: AsyncClient) -> None:
    """KYC application without auth must be rejected."""
    resp = await client.post(
        "/v1/accounts/kyc/apply",
        json={
            "category": "journalist",
            "organization": "Rappler",
            "bias_declaration": "Fact-based reporting.",
        },
    )
    assert resp.status_code in (401, 403), resp.text


# ---------------------------------------------------------------------------
# GET /v1/accounts/kyc/status
# ---------------------------------------------------------------------------


async def test_kyc_status(client: AsyncClient) -> None:
    """After applying for KYC, the status endpoint returns the application details."""
    reg = await _register(client)
    assert reg.status_code == 201
    api_key = reg.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    # Submit application first
    apply_resp = await client.post(
        "/v1/accounts/kyc/apply",
        json={
            "category": "academic",
            "organization": "UP Diliman",
            "bias_declaration": "Research-based perspective.",
        },
        headers=headers,
    )
    assert apply_resp.status_code == 201

    # Fetch status
    status_resp = await client.get("/v1/accounts/kyc/status", headers=headers)
    assert status_resp.status_code == 200, status_resp.text
    body = status_resp.json()
    assert "status" in body
    assert "category" in body
    assert "submitted_at" in body


async def test_kyc_status_no_application(client: AsyncClient) -> None:
    """Fetching KYC status when no application exists must return 404."""
    reg = await _register(client)
    assert reg.status_code == 201
    api_key = reg.json()["api_key"]

    resp = await client.get(
        "/v1/accounts/kyc/status",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# GET /v1/accounts/{username}/loob
# ---------------------------------------------------------------------------


async def test_get_loob(client: AsyncClient) -> None:
    """Registering a user auto-creates a Loob score; the public endpoint returns 5 dimensions."""
    username = unique_username()
    reg = await _register(client, username=username)
    assert reg.status_code == 201

    resp = await client.get(f"/v1/accounts/{username}/loob")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # All 5 Loob dimensions must be present
    for dimension in ["katapatan", "katumpakan", "kagalingan", "kapakumbabaan", "kalakarang_sibiko"]:
        assert dimension in body, f"Missing Loob dimension: {dimension}"
        assert isinstance(body[dimension], (int, float)), (
            f"Loob dimension '{dimension}' must be numeric, got {type(body[dimension])}"
        )


async def test_get_loob_user_not_found(client: AsyncClient) -> None:
    """Fetching Loob for a non-existent username must return 404."""
    resp = await client.get("/v1/accounts/definitely_nonexistent_user_xyz/loob")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


async def test_login_success(client: AsyncClient) -> None:
    """Login with valid credentials returns access_token."""
    username = unique_username()
    await _register(client, username)
    resp = await client.post(
        "/v1/accounts/login",
        json={"username": username, "password": "testpass123"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["access_token"].startswith("bobot_hum_")
    assert data["user"]["username"] == username
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient) -> None:
    """Login with wrong password returns 401."""
    username = unique_username()
    await _register(client, username)
    resp = await client.post(
        "/v1/accounts/login",
        json={"username": username, "password": "wrongpassword"},
    )
    assert resp.status_code == 401, resp.text


async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """Login with non-existent username returns 401."""
    resp = await client.post(
        "/v1/accounts/login",
        json={"username": "nonexistent_user_xyz", "password": "testpass123"},
    )
    assert resp.status_code == 401, resp.text


async def test_login_token_works_for_auth(client: AsyncClient) -> None:
    """Token from login can be used to access authenticated endpoints."""
    username = unique_username()
    await _register(client, username)
    login_resp = await client.post(
        "/v1/accounts/login",
        json={"username": username, "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    me_resp = await client.get(
        "/v1/accounts/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200, me_resp.text
    assert me_resp.json()["username"] == username

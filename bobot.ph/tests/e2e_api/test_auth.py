"""E2E tests for /v1/accounts/ endpoints."""

import uuid

import httpx
import pytest

from tests.e2e_api.conftest import auth_headers


def test_health(client: httpx.Client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_new_human(client: httpx.Client):
    uid = uuid.uuid4().hex[:8]
    resp = client.post(
        "/v1/accounts/register",
        json={
            "username": f"newuser_{uid}",
            "email": f"newuser_{uid}@test.ph",
            "password": "testpass123",
            "region": "Metro Manila",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    # Register returns: account_id, api_key, tier (no username field)
    assert "api_key" in data
    assert "account_id" in data


def test_register_duplicate_username(client: httpx.Client, manifest: dict):
    """Duplicate username with a valid email should return 409."""
    alice_username = manifest["humans"]["alice_e2e"]["username"]
    uid = uuid.uuid4().hex[:8]
    resp = client.post(
        "/v1/accounts/register",
        json={
            "username": alice_username,
            "email": f"different_dup_{uid}@test.ph",
            "password": "testpass123",
            "region": "Metro Manila",
        },
    )
    assert resp.status_code == 409


def test_login_success(client: httpx.Client):
    """Login returns access_token and user object — does NOT return api_key at top level.

    Uses a freshly registered user so we don't rotate alice/bob's keys mid-session.
    """
    uid = uuid.uuid4().hex[:8]
    username = f"logintest_{uid}"
    # Register a fresh user (region is required)
    reg = client.post(
        "/v1/accounts/register",
        json={
            "username": username,
            "email": f"{username}@test.ph",
            "password": "testpass123",
            "region": "Metro Manila",
        },
    )
    assert reg.status_code == 201

    resp = client.post(
        "/v1/accounts/login",
        json={"username": username, "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Login returns: access_token (not api_key), user object
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["username"] == username


def test_login_wrong_password(client: httpx.Client, manifest: dict):
    """Wrong password returns 401 — uses manifest username but wrong password (no key rotation)."""
    alice_username = manifest["humans"]["alice_e2e"]["username"]
    resp = client.post(
        "/v1/accounts/login",
        json={
            "username": alice_username,
            "password": "wrongpassword999",
        },
    )
    assert resp.status_code == 401


def test_get_profile(client: httpx.Client, alice: dict):
    """Use session-refreshed alice api_key (obtained by conftest login)."""
    resp = client.get("/v1/accounts/me", headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == alice["username"]
    assert "tier" in data


def test_update_profile(client: httpx.Client, bob: dict):
    resp = client.patch(
        "/v1/accounts/me",
        json={"bio": "E2E test user bob", "region": "Cebu"},
        headers=auth_headers(bob["api_key"]),
    )
    assert resp.status_code == 200
    assert resp.json()["region"] == "Cebu"

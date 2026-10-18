"""E2E tests for /v1/posts/ — citation enforcement is THE core feature."""

import httpx
import pytest

from tests.e2e_api.conftest import auth_headers


def test_feed_returns_seeded_posts(client: httpx.Client):
    resp = client.get("/v1/posts/", params={"baryo": "presyo", "sort": "new", "limit": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    assert len(data["posts"]) >= 3


def test_feed_sort_hot(client: httpx.Client):
    resp = client.get("/v1/posts/", params={"baryo": "presyo", "sort": "hot"})
    assert resp.status_code == 200
    assert "posts" in resp.json()


def test_feed_sort_top(client: httpx.Client):
    resp = client.get("/v1/posts/", params={"baryo": "presyo", "sort": "top"})
    assert resp.status_code == 200
    assert "posts" in resp.json()


def test_feed_filter_bots_only(client: httpx.Client):
    resp = client.get("/v1/posts/", params={"baryo": "presyo", "type": "bot"})
    assert resp.status_code == 200
    posts = resp.json()["posts"]
    assert all(p["author_type"] == "bot" for p in posts)


def test_feed_filter_verified_only(client: httpx.Client):
    resp = client.get("/v1/posts/", params={"sort": "verified_only"})
    assert resp.status_code == 200
    posts = resp.json()["posts"]
    assert all(p["confidence_tier"] == "verified" for p in posts)


def test_bot_create_post_with_citation(client: httpx.Client, presyo_bot: dict):
    resp = client.post(
        "/v1/posts/",
        json={
            "baryo": "presyo",
            "content": "E2E Test: bigas P48/kg sa NCR ngayong Marso.",
            "source_url": "https://dti.gov.ph/price-update-e2e-test",
            "confidence_tier": "verified",
            "skill_used": "PriceWatch",
        },
        headers=auth_headers(presyo_bot["api_key"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["author_type"] == "bot"
    assert data["source_url"] == "https://dti.gov.ph/price-update-e2e-test"
    assert data["baryo_name"] == "presyo"


def test_bot_post_without_citation_rejected(client: httpx.Client, presyo_bot: dict):
    resp = client.post(
        "/v1/posts/",
        json={
            "baryo": "presyo",
            "content": "Mahal ang bigas. Walang citation.",
        },
        headers=auth_headers(presyo_bot["api_key"]),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "CITATION_REQUIRED"


def test_bot_post_empty_citation_rejected(client: httpx.Client, presyo_bot: dict):
    resp = client.post(
        "/v1/posts/",
        json={
            "baryo": "presyo",
            "content": "Mahal ang bigas.",
            "source_url": "   ",
        },
        headers=auth_headers(presyo_bot["api_key"]),
    )
    assert resp.status_code == 400


def test_bot_domain_lock_enforced(client: httpx.Client, presyo_bot: dict):
    resp = client.post(
        "/v1/posts/",
        json={
            "baryo": "batas",
            "content": "Batas ng presyo.",
            "source_url": "https://lawphil.net/test-domain-lock",
        },
        headers=auth_headers(presyo_bot["api_key"]),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "DOMAIN_LOCK_VIOLATION"


def test_human_post_without_citation_allowed(client: httpx.Client, alice: dict):
    resp = client.post(
        "/v1/posts/",
        json={
            "baryo": "presyo",
            "content": "Nakita ko sa palengke, mahal talaga ang lahat! E2E human post.",
        },
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 201
    assert resp.json()["author_type"] == "human"


def test_get_single_post(client: httpx.Client):
    feed = client.get("/v1/posts/", params={"baryo": "presyo", "limit": 1}).json()
    post_id = feed["posts"][0]["id"]
    resp = client.get(f"/v1/posts/{post_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == post_id


def test_get_nonexistent_post(client: httpx.Client):
    resp = client.get("/v1/posts/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404

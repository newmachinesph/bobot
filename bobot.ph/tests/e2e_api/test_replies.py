"""E2E tests for threaded replies."""

import httpx
import pytest

from tests.e2e_api.conftest import auth_headers


def _get_presyo_post_id(client: httpx.Client) -> str:
    feed = client.get("/v1/posts/", params={"baryo": "presyo", "type": "bot", "limit": 1}).json()
    assert feed["posts"], "No presyo bot posts — run seed_e2e.py"
    return feed["posts"][0]["id"]


def test_human_reply_to_post(client: httpx.Client, alice: dict):
    post_id = _get_presyo_post_id(client)
    resp = client.post(
        f"/v1/posts/{post_id}/replies",
        json={"content": "Totoo ba ito? Checked ko sa palengke — E2E reply test."},
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["post_id"] == post_id
    # Top-level replies have depth=0
    assert data["depth"] == 0
    assert data["parent_id"] is None


def test_bot_reply_requires_citation(client: httpx.Client, presyo_bot: dict):
    post_id = _get_presyo_post_id(client)
    resp = client.post(
        f"/v1/posts/{post_id}/replies",
        json={"content": "Bot reply without citation."},
        headers=auth_headers(presyo_bot["api_key"]),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "CITATION_REQUIRED"


def test_bot_reply_with_citation(client: httpx.Client, presyo_bot: dict):
    post_id = _get_presyo_post_id(client)
    resp = client.post(
        f"/v1/posts/{post_id}/replies",
        json={
            "content": "Kumpirma ng DTI: P45/kg ang bigas sa Metro Manila — E2E bot reply.",
            "source_url": "https://dti.gov.ph/e2e-bot-reply-confirmation",
        },
        headers=auth_headers(presyo_bot["api_key"]),
    )
    assert resp.status_code == 201
    assert resp.json()["source_url"] == "https://dti.gov.ph/e2e-bot-reply-confirmation"


def test_nested_reply(client: httpx.Client, alice: dict, bob: dict):
    post_id = _get_presyo_post_id(client)

    # Alice posts top-level reply
    r1 = client.post(
        f"/v1/posts/{post_id}/replies",
        json={"content": "Alice top-level reply for nesting test."},
        headers=auth_headers(alice["api_key"]),
    ).json()

    # Bob replies to Alice's reply
    resp = client.post(
        f"/v1/posts/{post_id}/replies",
        params={"parent_id": r1["id"]},
        json={"content": "Bob nested reply — depth should be 1."},
        headers=auth_headers(bob["api_key"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["depth"] == 1
    assert data["parent_id"] == r1["id"]


def test_get_replies_returns_tree(client: httpx.Client):
    post_id = _get_presyo_post_id(client)
    resp = client.get(f"/v1/posts/{post_id}/replies")
    assert resp.status_code == 200
    replies = resp.json()
    assert isinstance(replies, list)
    for r in replies:
        assert "replies" in r
        assert "content" in r
        # The reply response uses author_name (not author_handle)
        assert "author_name" in r


def test_reply_to_nonexistent_post(client: httpx.Client, alice: dict):
    resp = client.post(
        "/v1/posts/00000000-0000-0000-0000-000000000000/replies",
        json={"content": "Ghost reply."},
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 404

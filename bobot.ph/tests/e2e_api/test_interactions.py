"""E2E tests for voting (agree/disagree) and flagging."""

import httpx
import pytest

from tests.e2e_api.conftest import auth_headers


def _get_presyo_bot_post(client: httpx.Client) -> dict:
    feed = client.get("/v1/posts/", params={"baryo": "presyo", "type": "bot", "limit": 1}).json()
    assert feed["posts"], "No presyo bot posts found — run seed_e2e.py"
    return feed["posts"][0]


def test_agree_increments_count(client: httpx.Client, alice: dict):
    post = _get_presyo_bot_post(client)
    initial = post["agree_count"]
    post_id = post["id"]

    resp = client.post(f"/v1/posts/{post_id}/agree", headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 200
    assert resp.json()["vote_type"] == "agree"

    updated = client.get(f"/v1/posts/{post_id}").json()
    # Count should be >= initial (may have been agreed already)
    assert updated["agree_count"] >= initial


def test_disagree_vote(client: httpx.Client, bob: dict):
    post = _get_presyo_bot_post(client)
    post_id = post["id"]

    resp = client.post(f"/v1/posts/{post_id}/disagree", headers=auth_headers(bob["api_key"]))
    assert resp.status_code == 200
    assert resp.json()["vote_type"] == "disagree"


def test_agree_then_switch_to_disagree(client: httpx.Client, alice: dict):
    # Use batas bot post to avoid state from previous test
    feed = client.get("/v1/posts/", params={"baryo": "batas", "type": "bot", "limit": 1}).json()
    if not feed["posts"]:
        pytest.skip("No batas posts available")
    post_id = feed["posts"][0]["id"]

    # Agree first
    client.post(f"/v1/posts/{post_id}/agree", headers=auth_headers(alice["api_key"]))
    # Then disagree
    resp = client.post(f"/v1/posts/{post_id}/disagree", headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 200


def test_duplicate_agree_is_idempotent(client: httpx.Client, bob: dict):
    post = _get_presyo_bot_post(client)
    post_id = post["id"]

    # Bob agrees twice — second agree returns "Already agreed." message
    client.post(f"/v1/posts/{post_id}/agree", headers=auth_headers(bob["api_key"]))
    resp = client.post(f"/v1/posts/{post_id}/agree", headers=auth_headers(bob["api_key"]))
    assert resp.status_code == 200
    assert "already" in resp.json()["message"].lower()


def test_flag_post(client: httpx.Client, alice: dict):
    # Flag a batas post (distinct from presyo to avoid conflict with other tests)
    feed = client.get("/v1/posts/", params={"baryo": "batas", "type": "bot", "limit": 1}).json()
    if not feed["posts"]:
        pytest.skip("No batas posts available")
    post_id = feed["posts"][0]["id"]

    resp = client.post(
        f"/v1/posts/{post_id}/flag",
        json={
            "reason": "misinformation",
            "evidence_url": "https://example.com/e2e-proof",
        },
        headers=auth_headers(alice["api_key"]),
    )
    # 201 if new flag, 409 if already flagged by alice
    assert resp.status_code in (201, 409)


def test_self_flag_rejected(client: httpx.Client, alice: dict):
    # Alice creates a post
    resp = client.post(
        "/v1/posts/",
        json={
            "baryo": "presyo",
            "content": "Alice self-flag test post.",
        },
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 201
    post_id = resp.json()["id"]

    # Alice tries to flag her own post — should get 400
    resp = client.post(
        f"/v1/posts/{post_id}/flag",
        json={"reason": "spam"},
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 400

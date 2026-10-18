"""E2E tests for /v1/messages/ endpoints.

Endpoint map (prefix = /v1/messages):
  GET  /check                           — DM inbox activity poll
  POST /request                         — send a DM request
  GET  /requests                        — list pending requests (recipient's view)
  POST /requests/{id}/approve           — approve a pending request
  POST /requests/{id}/reject            — reject a pending request
  GET  /conversations                   — list approved conversations
  GET  /conversations/{id}              — read conversation messages
  POST /conversations/{id}/send         — send message in approved conversation
"""

import httpx
import pytest

from tests.e2e_api.conftest import auth_headers


# ---------------------------------------------------------------------------
# 1. Check DM inbox
# ---------------------------------------------------------------------------


def test_check_inbox_alice(client: httpx.Client, alice: dict):
    """GET /v1/messages/check should return 200 with activity fields."""
    resp = client.get("/v1/messages/check", headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "has_activity" in data
    assert "pending_requests" in data
    assert "unread_messages" in data
    assert "requests" in data


def test_check_inbox_bot(client: httpx.Client, presyo_bot: dict):
    """Bots can also poll the DM inbox."""
    resp = client.get("/v1/messages/check", headers=auth_headers(presyo_bot["api_key"]))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "has_activity" in data


# ---------------------------------------------------------------------------
# 2. Send a message request from alice to presyo_bot
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def conversation_id(client: httpx.Client, alice: dict, presyo_bot: dict) -> str:
    """Send a DM request from alice to PresyoBot_E2E; return conversation_id.

    Handles all states: new pending (201), already pending (409), already
    approved (409 with different message). In all 409 cases we retrieve the
    conversation_id from either the pending requests list (bot's view) or the
    approved conversations list (alice's view).
    """
    resp = client.post(
        "/v1/messages/request",
        headers=auth_headers(alice["api_key"]),
        json={
            "to": presyo_bot["handle"],
            "message": "Magandang araw! May tanong ako tungkol sa presyo ng bigas.",
        },
    )
    # 201 = new request created
    assert resp.status_code in (201, 409), resp.text

    if resp.status_code == 201:
        data = resp.json()
        assert "conversation_id" in data
        return data["conversation_id"]

    # 409 — conversation already exists in some state; find the id

    # Check approved conversations (alice's view)
    convs_resp = client.get(
        "/v1/messages/conversations",
        headers=auth_headers(alice["api_key"]),
    )
    if convs_resp.status_code == 200:
        for c in convs_resp.json().get("conversations", []):
            if c.get("with_user", {}).get("name") == presyo_bot["handle"]:
                return c["conversation_id"]

    # Check pending requests (bot's view — bot sees pending requests sent TO it)
    req_resp = client.get(
        "/v1/messages/requests",
        headers=auth_headers(presyo_bot["api_key"]),
    )
    if req_resp.status_code == 200:
        for r in req_resp.json():
            if r.get("from_user", {}).get("name") == alice.get("username"):
                return r["conversation_id"]

    pytest.skip("Could not recover conversation_id from existing state")


def test_send_dm_request_alice_to_presyo(client: httpx.Client, alice: dict, presyo_bot: dict):
    """POST /v1/messages/request — sends request and returns 201 or 409 if already pending."""
    resp = client.post(
        "/v1/messages/request",
        headers=auth_headers(alice["api_key"]),
        json={
            "to": presyo_bot["handle"],
            "message": "Kumusta? Test message.",
        },
    )
    assert resp.status_code in (201, 409), resp.text


# ---------------------------------------------------------------------------
# 3. Get pending requests for presyo_bot
# ---------------------------------------------------------------------------


def test_get_pending_requests_presyo_bot(client: httpx.Client, presyo_bot: dict):
    """GET /v1/messages/requests — presyo_bot sees incoming pending requests."""
    resp = client.get(
        "/v1/messages/requests",
        headers=auth_headers(presyo_bot["api_key"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# 4. Approve the request as presyo_bot
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def approved_conversation_id(
    client: httpx.Client, alice: dict, presyo_bot: dict, conversation_id: str
) -> str:
    """Approve the pending request as presyo_bot; return conversation_id."""
    # First check if already approved
    convs_resp = client.get(
        "/v1/messages/conversations",
        headers=auth_headers(presyo_bot["api_key"]),
    )
    if convs_resp.status_code == 200:
        for c in convs_resp.json().get("conversations", []):
            if c.get("with_user", {}).get("name") == alice.get("username"):
                return c["conversation_id"]

    # Try to approve
    resp = client.post(
        f"/v1/messages/requests/{conversation_id}/approve",
        headers=auth_headers(presyo_bot["api_key"]),
    )
    # 200 = approved; 400 = already approved (ok)
    assert resp.status_code in (200, 400), resp.text
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "approved"
        return data["conversation_id"]
    # Already approved — return original id
    return conversation_id


def test_approve_request_as_presyo_bot(
    client: httpx.Client, alice: dict, presyo_bot: dict, conversation_id: str
):
    """POST /v1/messages/requests/{id}/approve — presyo_bot approves request."""
    resp = client.post(
        f"/v1/messages/requests/{conversation_id}/approve",
        headers=auth_headers(presyo_bot["api_key"]),
    )
    # 200 = approved now; 400 = already approved (idempotent re-run)
    assert resp.status_code in (200, 400), resp.text
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "approved"
        assert "conversation_id" in data


# ---------------------------------------------------------------------------
# 5. Send a message in the approved conversation
# ---------------------------------------------------------------------------


def test_send_message_in_conversation(
    client: httpx.Client, alice: dict, approved_conversation_id: str
):
    """POST /v1/messages/conversations/{id}/send — alice sends a message."""
    resp = client.post(
        f"/v1/messages/conversations/{approved_conversation_id}/send",
        headers=auth_headers(alice["api_key"]),
        json={"message": "Magkano ang isang kilo ng bigas ngayon?"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert "content" in data
    assert data["content"] == "Magkano ang isang kilo ng bigas ngayon?"
    assert "sender" in data


def test_list_conversations_alice(client: httpx.Client, alice: dict):
    """GET /v1/messages/conversations — alice sees her approved conversations."""
    resp = client.get(
        "/v1/messages/conversations",
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "conversations" in data
    assert "total" in data
    assert isinstance(data["conversations"], list)


def test_read_conversation_messages(
    client: httpx.Client, alice: dict, approved_conversation_id: str
):
    """GET /v1/messages/conversations/{id} — alice reads the conversation."""
    resp = client.get(
        f"/v1/messages/conversations/{approved_conversation_id}",
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "messages" in data
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) >= 1

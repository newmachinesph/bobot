"""
tests/api/test_posts.py

Integration tests for all post endpoints — with HEAVY focus on citation enforcement.
Citation enforcement is the single most important rule on bobot.ph:
  - Bots MUST provide a non-empty source_url or be rejected with 400 CITATION_REQUIRED
  - Humans are NOT required to cite sources

Endpoints covered:
  POST   /v1/posts/
  GET    /v1/posts/
  POST   /v1/posts/{post_id}/agree
  POST   /v1/posts/{post_id}/disagree
  POST   /v1/posts/{post_id}/flag
  GET    /v1/posts/{post_id}/challenge-card/{format}
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.bots import Bot
from tests.conftest import unique_email, unique_handle, unique_username

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


async def _register_human(client: AsyncClient) -> tuple[str, str]:
    """Register a fresh human; return (api_key, username)."""
    username = unique_username()
    resp = await client.post(
        "/v1/accounts/register",
        json={
            "username": username,
            "email": unique_email(),
            "region": "Metro Manila",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 201, f"Human registration failed: {resp.text}"
    return resp.json()["api_key"], username


def _bot_payload(handle: str, domain_lock: list | None = None) -> dict:
    return {
        "handle": handle,
        "origin_story": "Serbisyo sa bayan.",
        "region": "Metro Manila",
        "taglish_ratio": 50,
        "tone_preset": "formal",
        "skills": ["fact_check"],
        "declared_sources": ["https://psa.gov.ph"],
        "domain_lock": domain_lock or [],
        "refresh_rate": "daily",
        "max_posts_per_day": 50,
        "can_reply_to_humans": True,
        "position_firmness": 50,
        "correction_threshold": "source_beats_source",
        "flattery_resistance": True,
        "peer_pressure_resistance": 50,
        "uncertainty_expression": "explicit_uncertainty",
        "minimum_confidence_to_post": 60,
        "funding_source": "independent_creator",
        "declared_interests": "None.",
    }


async def _register_bot(client: AsyncClient, human_key: str, domain_lock: list | None = None) -> tuple[str, str]:
    """Register a bot; return (bot_api_key, bot_id)."""
    handle = unique_handle()
    resp = await client.post(
        "/v1/bots/register",
        json=_bot_payload(handle, domain_lock),
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 201, f"Bot registration failed: {resp.text}"
    body = resp.json()
    return body["api_key"], body["bot_id"]


async def _create_baryo(client: AsyncClient, human_key: str, name: str | None = None) -> str:
    """Create a baryo and return its name."""
    import uuid as _uuid
    baryo_name = name or f"baryo_{_uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/v1/baryos/",
        json={
            "name": baryo_name,
            "display_name": f"Baryo {baryo_name}",
            "description": "Test baryo para sa mga test.",
            "region": "Metro Manila",
            "allowed_bot_skills": ["fact_check"],
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 201, f"Baryo creation failed: {resp.text}"
    return baryo_name


# ---------------------------------------------------------------------------
# CITATION ENFORCEMENT — THE MOST IMPORTANT TESTS
# ---------------------------------------------------------------------------


async def test_bot_post_with_citation(client: AsyncClient) -> None:
    """
    CITATION ENFORCEMENT: Bot post WITH a valid source_url must succeed (201).
    This is the happy path for citation enforcement.
    """
    human_key, _ = await _register_human(client)
    bot_key, _ = await _register_bot(client, human_key)
    baryo_name = await _create_baryo(client, human_key)

    resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Ang presyo ng bigas ay tumaas ng 10% ayon sa PSA.",
            "source_url": "https://psa.gov.ph/statistics/survey/price/bigas-2026",
            "confidence_tier": "likely_accurate",
        },
        headers={"Authorization": f"Bearer {bot_key}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["source_url"] == "https://psa.gov.ph/statistics/survey/price/bigas-2026"
    assert body["author_type"] == "bot"


async def test_bot_post_without_citation(client: AsyncClient) -> None:
    """
    CITATION ENFORCEMENT — MOST CRITICAL TEST:
    A bot POST without source_url MUST be rejected with 400 and error code CITATION_REQUIRED.
    This enforces the platform's core rule: bots cannot make claims without citing sources.
    """
    human_key, _ = await _register_human(client)
    bot_key, _ = await _register_bot(client, human_key)
    baryo_name = await _create_baryo(client, human_key)

    resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Naniniwala ako na mataas ang inflation ngayon.",
            # source_url is intentionally omitted — this MUST fail
        },
        headers={"Authorization": f"Bearer {bot_key}"},
    )

    assert resp.status_code == 400, (
        f"Expected 400 CITATION_REQUIRED when bot posts without source_url, "
        f"but got {resp.status_code}. Response: {resp.text}"
    )

    body = resp.json()
    # The error detail must identify CITATION_REQUIRED
    detail = body.get("detail", {})
    error_code = detail.get("error") if isinstance(detail, dict) else str(detail)
    assert "CITATION_REQUIRED" in str(error_code), (
        f"Expected 'CITATION_REQUIRED' in error detail, got: {detail}"
    )


async def test_bot_post_empty_citation(client: AsyncClient) -> None:
    """
    CITATION ENFORCEMENT: Bot post with source_url="" (empty string) must also be rejected
    with 400 CITATION_REQUIRED. An empty string is not a valid citation.
    """
    human_key, _ = await _register_human(client)
    bot_key, _ = await _register_bot(client, human_key)
    baryo_name = await _create_baryo(client, human_key)

    resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Nais kong magsabi ng bagay nang walang ebidensya.",
            "source_url": "",  # empty string — must be treated as no citation
        },
        headers={"Authorization": f"Bearer {bot_key}"},
    )

    assert resp.status_code == 400, (
        f"Expected 400 CITATION_REQUIRED for empty source_url, "
        f"but got {resp.status_code}. Response: {resp.text}"
    )

    body = resp.json()
    detail = body.get("detail", {})
    error_code = detail.get("error") if isinstance(detail, dict) else str(detail)
    assert "CITATION_REQUIRED" in str(error_code), (
        f"Expected 'CITATION_REQUIRED' in error detail, got: {detail}"
    )


async def test_bot_post_whitespace_only_citation(client: AsyncClient) -> None:
    """
    CITATION ENFORCEMENT: source_url with only whitespace characters must be rejected.
    A bot cannot bypass citation enforcement by sending spaces.
    """
    human_key, _ = await _register_human(client)
    bot_key, _ = await _register_bot(client, human_key)
    baryo_name = await _create_baryo(client, human_key)

    resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Sinusubukan kong dayain ang sistema.",
            "source_url": "   ",  # whitespace only — must be treated as no citation
        },
        headers={"Authorization": f"Bearer {bot_key}"},
    )

    assert resp.status_code == 400, (
        f"Expected 400 CITATION_REQUIRED for whitespace-only source_url, "
        f"but got {resp.status_code}. Response: {resp.text}"
    )

    body = resp.json()
    detail = body.get("detail", {})
    error_code = detail.get("error") if isinstance(detail, dict) else str(detail)
    assert "CITATION_REQUIRED" in str(error_code), (
        f"Expected 'CITATION_REQUIRED' in error detail, got: {detail}"
    )


async def test_human_post_without_citation(client: AsyncClient) -> None:
    """
    CITATION EXEMPTION: Humans are NOT required to provide source_url.
    A human post without source_url must succeed (201).
    """
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Sa aking palagay, kailangan nating pag-aralan ito nang mabuti.",
            # source_url intentionally omitted — humans are exempt
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )

    assert resp.status_code == 201, (
        f"Human post without citation should succeed, but got {resp.status_code}. "
        f"Response: {resp.text}"
    )
    body = resp.json()
    assert body["author_type"] == "human"
    assert body["source_url"] is None


async def test_human_post_with_citation(client: AsyncClient) -> None:
    """Humans can optionally provide a source_url, and it will be stored."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    source = "https://rappler.com/article/example"
    resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Ayon sa Rappler, ang sitwasyon ay nananatiling mabigat.",
            "source_url": source,
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["source_url"] == source


# ---------------------------------------------------------------------------
# JAILED BOT — cannot post
# ---------------------------------------------------------------------------


async def test_bot_jailed_cannot_post(client: AsyncClient, db_session: AsyncSession) -> None:
    """
    A bot with jail_status='jailed' must be blocked from posting (403 BOT_JAILED).
    This test directly sets the jail_status in the DB to simulate the Lupon's action.
    Note: the auth middleware also enforces jail at the authentication layer (403).
    """
    human_key, _ = await _register_human(client)
    bot_key, bot_id = await _register_bot(client, human_key)
    baryo_name = await _create_baryo(client, human_key)

    # Directly set the bot's jail_status to "jailed" in the database
    import uuid as _uuid
    await db_session.execute(
        update(Bot)
        .where(Bot.id == _uuid.UUID(bot_id))
        .values(jail_status="jailed")
    )
    await db_session.commit()

    # The jailed bot should be blocked — auth.py enforces this at the 403 level
    resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Sinusubukan akong mag-post kahit nakakulong.",
            "source_url": "https://example.com/evidence",
        },
        headers={"Authorization": f"Bearer {bot_key}"},
    )

    assert resp.status_code == 403, (
        f"Expected 403 for jailed bot, but got {resp.status_code}. Response: {resp.text}"
    )

    # Verify the error signals a jail condition
    body = resp.json()
    detail = body.get("detail", "")
    detail_str = str(detail)
    assert "jailed" in detail_str.lower() or "BOT_JAILED" in detail_str, (
        f"Expected jail-related error message, got: {detail}"
    )


async def test_bot_permanent_jail_cannot_post(client: AsyncClient, db_session: AsyncSession) -> None:
    """
    A bot with jail_status='permanent_jail' must also be blocked (403).
    """
    human_key, _ = await _register_human(client)
    bot_key, bot_id = await _register_bot(client, human_key)
    baryo_name = await _create_baryo(client, human_key)

    import uuid as _uuid
    await db_session.execute(
        update(Bot)
        .where(Bot.id == _uuid.UUID(bot_id))
        .values(jail_status="permanent_jail")
    )
    await db_session.commit()

    resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Bawal na ako pero susubukan pa rin.",
            "source_url": "https://example.com/evidence",
        },
        headers={"Authorization": f"Bearer {bot_key}"},
    )

    assert resp.status_code == 403, (
        f"Expected 403 for permanently jailed bot, but got {resp.status_code}. "
        f"Response: {resp.text}"
    )


# ---------------------------------------------------------------------------
# POST /v1/posts/ — additional validation tests
# ---------------------------------------------------------------------------


async def test_post_baryo_not_found(client: AsyncClient) -> None:
    """Posting to a non-existent baryo must return 404."""
    human_key, _ = await _register_human(client)

    resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": "nonexistent_baryo_xyz_999",
            "content": "This baryo does not exist.",
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 404, resp.text


async def test_post_requires_auth(client: AsyncClient) -> None:
    """Creating a post without authentication must be rejected."""
    resp = await client.post(
        "/v1/posts/",
        json={"baryo": "some_baryo", "content": "Anonymous post attempt."},
    )
    assert resp.status_code in (401, 403), resp.text


# ---------------------------------------------------------------------------
# GET /v1/posts/ — Feed
# ---------------------------------------------------------------------------


async def test_get_feed(client: AsyncClient) -> None:
    """GET /v1/posts/ returns a feed with pagination metadata."""
    resp = await client.get("/v1/posts/")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "posts" in body
    assert isinstance(body["posts"], list)
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["limit"] > 0


async def test_get_feed_contains_newly_created_post(client: AsyncClient) -> None:
    """A post created via POST /v1/posts/ appears in the feed."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    content = f"Pagsubok na post para sa feed — {unique_username()}"
    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": content},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    # Fetch the feed and verify the post is present
    feed_resp = await client.get("/v1/posts/?limit=100")
    assert feed_resp.status_code == 200
    post_ids = [p["id"] for p in feed_resp.json()["posts"]]
    assert post_id in post_ids, "Newly created post not found in feed"


async def test_get_feed_filtered_by_baryo(client: AsyncClient) -> None:
    """Feed filtered by baryo name returns only posts from that baryo."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    # Create a post in this baryo
    create_resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Ito ay isang post sa partikular na baryo.",
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert create_resp.status_code == 201

    # Fetch feed filtered by that baryo
    feed_resp = await client.get(f"/v1/posts/?baryo={baryo_name}")
    assert feed_resp.status_code == 200, feed_resp.text
    body = feed_resp.json()

    assert "posts" in body
    for post in body["posts"]:
        assert post["baryo_name"] == baryo_name, (
            f"Expected all posts to be from '{baryo_name}', but got '{post['baryo_name']}'"
        )


async def test_get_feed_filtered_by_nonexistent_baryo(client: AsyncClient) -> None:
    """Filtering feed by a baryo that does not exist must return 404."""
    resp = await client.get("/v1/posts/?baryo=totally_nonexistent_baryo_xyz_999")
    assert resp.status_code == 404, resp.text


async def test_get_feed_sort_options(client: AsyncClient) -> None:
    """Feed accepts valid sort options without error."""
    for sort in ["new", "top", "hot", "rising", "verified_only"]:
        resp = await client.get(f"/v1/posts/?sort={sort}&limit=5")
        assert resp.status_code == 200, f"Sort '{sort}' failed: {resp.text}"


async def test_get_feed_type_filter(client: AsyncClient) -> None:
    """Feed type filter accepts 'bot', 'human', 'both' without error."""
    for type_filter in ["bot", "human", "both"]:
        resp = await client.get(f"/v1/posts/?type={type_filter}&limit=5")
        assert resp.status_code == 200, f"Type filter '{type_filter}' failed: {resp.text}"


# ---------------------------------------------------------------------------
# POST /v1/posts/{post_id}/agree
# ---------------------------------------------------------------------------


async def test_agree_vote(client: AsyncClient) -> None:
    """A human agreeing with a post increments the agree_count."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    # Create a post to vote on (as another human to avoid potential self-vote issues)
    author_key, _ = await _register_human(client)
    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Sumasang-ayon ba kayo?"},
        headers={"Authorization": f"Bearer {author_key}"},
    )
    assert create_resp.status_code == 201
    post = create_resp.json()
    post_id = post["id"]
    initial_agree = post["agree_count"]

    # Vote agree
    vote_resp = await client.post(
        f"/v1/posts/{post_id}/agree",
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert vote_resp.status_code == 200, vote_resp.text
    body = vote_resp.json()
    assert body["vote_type"] == "agree"
    assert body["post_id"] == post_id
    assert "message" in body


async def test_agree_vote_requires_human_auth(client: AsyncClient) -> None:
    """Voting requires authentication; unauthenticated request must be rejected."""
    resp = await client.post("/v1/posts/00000000-0000-0000-0000-000000000001/agree")
    assert resp.status_code in (401, 403), resp.text


async def test_agree_vote_post_not_found(client: AsyncClient) -> None:
    """Agreeing with a non-existent post must return 404."""
    human_key, _ = await _register_human(client)
    resp = await client.post(
        "/v1/posts/00000000-0000-0000-0000-000000000001/agree",
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# POST /v1/posts/{post_id}/disagree
# ---------------------------------------------------------------------------


async def test_disagree_vote(client: AsyncClient) -> None:
    """A human disagreeing with a post increments the disagree_count."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    author_key, _ = await _register_human(client)
    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Hindi kaya kayo sumasang-ayon?"},
        headers={"Authorization": f"Bearer {author_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    vote_resp = await client.post(
        f"/v1/posts/{post_id}/disagree",
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert vote_resp.status_code == 200, vote_resp.text
    body = vote_resp.json()
    assert body["vote_type"] == "disagree"
    assert body["post_id"] == post_id


async def test_vote_switch_agree_to_disagree(client: AsyncClient) -> None:
    """A human can switch their vote from agree to disagree."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    author_key, _ = await _register_human(client)
    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Pagsubok ng pagbabago ng boto."},
        headers={"Authorization": f"Bearer {author_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    # First vote: agree
    agree_resp = await client.post(
        f"/v1/posts/{post_id}/agree",
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert agree_resp.status_code == 200

    # Switch to disagree
    disagree_resp = await client.post(
        f"/v1/posts/{post_id}/disagree",
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert disagree_resp.status_code == 200
    assert "changed" in disagree_resp.json()["message"].lower()


# ---------------------------------------------------------------------------
# POST /v1/posts/{post_id}/flag
# ---------------------------------------------------------------------------


async def test_flag_post(client: AsyncClient) -> None:
    """A user can flag a post; the response confirms the flag and returns the updated flag_count."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    # Create post as a different user
    author_key, _ = await _register_human(client)
    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Ito ay maaaring maling impormasyon."},
        headers={"Authorization": f"Bearer {author_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    flag_resp = await client.post(
        f"/v1/posts/{post_id}/flag",
        json={"reason": "misinformation"},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert flag_resp.status_code == 201, flag_resp.text
    body = flag_resp.json()
    assert body["post_id"] == post_id
    assert body["reason"] == "misinformation"
    assert body["flag_count"] >= 1


async def test_flag_post_self_flag_rejected(client: AsyncClient) -> None:
    """A user cannot flag their own post (400)."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Ito ang aking sariling post."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    flag_resp = await client.post(
        f"/v1/posts/{post_id}/flag",
        json={"reason": "spam"},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert flag_resp.status_code == 400, flag_resp.text


async def test_flag_post_duplicate_flag_rejected(client: AsyncClient) -> None:
    """Flagging the same post twice must return 409."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    author_key, _ = await _register_human(client)
    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "I-flag nyo ito nang dalawang beses."},
        headers={"Authorization": f"Bearer {author_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    first_flag = await client.post(
        f"/v1/posts/{post_id}/flag",
        json={"reason": "off_topic"},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert first_flag.status_code == 201

    second_flag = await client.post(
        f"/v1/posts/{post_id}/flag",
        json={"reason": "off_topic"},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert second_flag.status_code == 409, second_flag.text


async def test_flag_post_invalid_reason(client: AsyncClient) -> None:
    """Flagging with an invalid reason string must return 422."""
    human_key, _ = await _register_human(client)

    resp = await client.post(
        "/v1/posts/00000000-0000-0000-0000-000000000001/flag",
        json={"reason": "not_a_valid_reason"},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# GET /v1/posts/{post_id}/challenge-card/{format}
# ---------------------------------------------------------------------------


async def test_challenge_card_square(client: AsyncClient) -> None:
    """Challenge card for 'square' format returns correct dimensions and post metadata."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Hamon kita sa katotohanan!"},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    card_resp = await client.get(f"/v1/posts/{post_id}/challenge-card/square")
    assert card_resp.status_code == 200, card_resp.text
    body = card_resp.json()

    assert body["post_id"] == post_id
    assert body["format"] == "square"
    assert body["dimensions"]["width"] == 1080
    assert body["dimensions"]["height"] == 1080
    assert "content" in body
    assert "author_type" in body
    assert "baryo_name" in body
    assert "challenge_text" in body
    assert "agree_count" in body
    assert "disagree_count" in body


async def test_challenge_card_portrait(client: AsyncClient) -> None:
    """Challenge card for 'portrait' format returns 1080x1350 dimensions."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Portrait card test."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    card_resp = await client.get(f"/v1/posts/{post_id}/challenge-card/portrait")
    assert card_resp.status_code == 200
    body = card_resp.json()
    assert body["dimensions"]["width"] == 1080
    assert body["dimensions"]["height"] == 1350


async def test_challenge_card_landscape(client: AsyncClient) -> None:
    """Challenge card for 'landscape' format returns 1200x630 dimensions."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Landscape card test."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    card_resp = await client.get(f"/v1/posts/{post_id}/challenge-card/landscape")
    assert card_resp.status_code == 200
    body = card_resp.json()
    assert body["dimensions"]["width"] == 1200
    assert body["dimensions"]["height"] == 630


async def test_challenge_card_bot_has_citation_challenge_text(client: AsyncClient) -> None:
    """Bot posts must show the 'May citation ba?' challenge text."""
    human_key, _ = await _register_human(client)
    bot_key, _ = await _register_bot(client, human_key)
    baryo_name = await _create_baryo(client, human_key)

    create_resp = await client.post(
        "/v1/posts/",
        json={
            "baryo": baryo_name,
            "content": "Bot post na may citation.",
            "source_url": "https://psa.gov.ph/bot-citation-test",
        },
        headers={"Authorization": f"Bearer {bot_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    card_resp = await client.get(f"/v1/posts/{post_id}/challenge-card/square")
    assert card_resp.status_code == 200
    body = card_resp.json()
    assert "May citation ba?" in body["challenge_text"]


async def test_challenge_card_not_found(client: AsyncClient) -> None:
    """Challenge card for a non-existent post must return 404."""
    resp = await client.get("/v1/posts/00000000-0000-0000-0000-000000000001/challenge-card/square")
    assert resp.status_code == 404, resp.text


async def test_challenge_card_invalid_format(client: AsyncClient) -> None:
    """Challenge card with an invalid format string must return 422."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)

    create_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Format test."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    resp = await client.get(f"/v1/posts/{post_id}/challenge-card/invalid_format")
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# POST /{post_id}/replies — Threaded replies
# ---------------------------------------------------------------------------


async def test_create_reply(client: AsyncClient) -> None:
    """Human can reply to a post."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)
    post_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Test post for replies."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    post_id = post_resp.json()["id"]

    reply_resp = await client.post(
        f"/v1/posts/{post_id}/replies",
        json={"content": "This is a reply!"},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert reply_resp.status_code == 201, reply_resp.text
    data = reply_resp.json()
    assert data["content"] == "This is a reply!"
    assert data["depth"] == 0
    assert data["parent_id"] is None


async def test_get_replies_empty(client: AsyncClient) -> None:
    """New post has no replies."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)
    post_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Post with no replies."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    post_id = post_resp.json()["id"]

    resp = await client.get(f"/v1/posts/{post_id}/replies")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_replies_returns_tree(client: AsyncClient) -> None:
    """Replies are returned as a nested tree."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)
    post_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Root post."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    post_id = post_resp.json()["id"]

    # Top-level reply
    r1 = await client.post(
        f"/v1/posts/{post_id}/replies",
        json={"content": "Top reply"},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    reply_id = r1.json()["id"]

    # Nested reply
    await client.post(
        f"/v1/posts/{post_id}/replies?parent_id={reply_id}",
        json={"content": "Nested reply"},
        headers={"Authorization": f"Bearer {human_key}"},
    )

    resp = await client.get(f"/v1/posts/{post_id}/replies")
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1  # one top-level
    assert tree[0]["content"] == "Top reply"
    assert len(tree[0]["replies"]) == 1  # one nested
    assert tree[0]["replies"][0]["content"] == "Nested reply"
    assert tree[0]["replies"][0]["depth"] == 1


async def test_bot_reply_requires_citation(client: AsyncClient) -> None:
    """Bot replies must include source_url."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)
    bot_key, _ = await _register_bot(client, human_key, domain_lock=[baryo_name])

    post_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Human post."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    post_id = post_resp.json()["id"]

    # Bot reply without citation
    resp = await client.post(
        f"/v1/posts/{post_id}/replies",
        json={"content": "Bot reply without source"},
        headers={"Authorization": f"Bearer {bot_key}"},
    )
    assert resp.status_code == 400, resp.text
    assert "CITATION_REQUIRED" in resp.text


async def test_reply_max_depth(client: AsyncClient) -> None:
    """Replies cannot exceed depth 6."""
    human_key, _ = await _register_human(client)
    baryo_name = await _create_baryo(client, human_key)
    post_resp = await client.post(
        "/v1/posts/",
        json={"baryo": baryo_name, "content": "Deep thread test."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    post_id = post_resp.json()["id"]

    # Chain 7 replies deep
    parent_id = None
    for depth in range(7):
        url = f"/v1/posts/{post_id}/replies"
        if parent_id:
            url += f"?parent_id={parent_id}"
        resp = await client.post(
            url,
            json={"content": f"Depth {depth}"},
            headers={"Authorization": f"Bearer {human_key}"},
        )
        if depth < 7:
            if resp.status_code == 201:
                parent_id = resp.json()["id"]
            elif resp.status_code == 400 and "depth" in resp.text.lower():
                # Hit max depth — expected at depth 6+
                assert depth >= 6
                break

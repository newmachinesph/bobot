"""
tests/api/test_citations.py

Integration tests for citation verification endpoints:
  POST   /v1/citations/verify
  GET    /v1/citations/verify/{job_id}
"""

import pytest
from httpx import AsyncClient

from tests.conftest import unique_email, unique_username

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


async def _register_bot(client: AsyncClient, human_key: str) -> str:
    """Register a bot and return the bot api_key."""
    from tests.conftest import unique_handle
    handle = unique_handle()
    resp = await client.post(
        "/v1/bots/register",
        json={
            "handle": handle,
            "origin_story": "Para sa serbisyo.",
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
    return resp.json()["api_key"]


# ---------------------------------------------------------------------------
# POST /v1/citations/verify
# ---------------------------------------------------------------------------


async def test_verify_citation_as_human(client: AsyncClient) -> None:
    """An authenticated human can submit a URL for citation verification."""
    human_key = await _register_human(client)

    resp = await client.post(
        "/v1/citations/verify",
        json={
            "url": "https://psa.gov.ph/statistics/survey/price/consumer-price-index",
            "claimed_content": (
                "The Consumer Price Index in the Philippines rose by 3.2% in January 2026."
            ),
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "job_id" in body, "Response must contain a job_id"
    assert body["status"] == "queued", (
        f"Expected status 'queued', got '{body['status']}'"
    )
    assert "estimated_seconds" in body
    assert isinstance(body["estimated_seconds"], int)


async def test_verify_citation_as_bot(client: AsyncClient) -> None:
    """An authenticated bot can also submit a URL for citation verification."""
    human_key = await _register_human(client)
    bot_key = await _register_bot(client, human_key)

    resp = await client.post(
        "/v1/citations/verify",
        json={
            "url": "https://bangko.gov.ph/inflation-data",
            "claimed_content": (
                "The Bangko Sentral ng Pilipinas reported inflation at 4.1% for Q1 2026."
            ),
        },
        headers={"Authorization": f"Bearer {bot_key}"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "job_id" in body
    assert body["status"] == "queued"


async def test_verify_citation_returns_unique_job_ids(client: AsyncClient) -> None:
    """Each verification request must return a unique job_id."""
    human_key = await _register_human(client)

    payload = {
        "url": "https://psa.gov.ph/statistics/survey/price/rice",
        "claimed_content": "Rice prices increased by 10% this quarter.",
    }

    resp1 = await client.post(
        "/v1/citations/verify",
        json=payload,
        headers={"Authorization": f"Bearer {human_key}"},
    )
    resp2 = await client.post(
        "/v1/citations/verify",
        json=payload,
        headers={"Authorization": f"Bearer {human_key}"},
    )

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["job_id"] != resp2.json()["job_id"], (
        "Each verification request must generate a unique job_id"
    )


async def test_verify_citation_requires_auth(client: AsyncClient) -> None:
    """Citation verification without authentication must be rejected."""
    resp = await client.post(
        "/v1/citations/verify",
        json={
            "url": "https://example.com",
            "claimed_content": "Some claimed content that is at least 10 characters long.",
        },
    )
    assert resp.status_code in (401, 403), resp.text


async def test_verify_citation_missing_url(client: AsyncClient) -> None:
    """Submitting a verification request without the URL must return 422."""
    human_key = await _register_human(client)

    resp = await client.post(
        "/v1/citations/verify",
        json={"claimed_content": "Content without URL, at least 10 chars."},
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 422, resp.text


async def test_verify_citation_short_claimed_content(client: AsyncClient) -> None:
    """claimed_content shorter than 10 characters must return 422 (min_length validation)."""
    human_key = await _register_human(client)

    resp = await client.post(
        "/v1/citations/verify",
        json={
            "url": "https://example.com",
            "claimed_content": "Too short",  # only 9 characters
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# GET /v1/citations/verify/{job_id}
# ---------------------------------------------------------------------------


async def test_get_citation_status(client: AsyncClient) -> None:
    """After submitting a verification request, polling the job_id returns the status."""
    human_key = await _register_human(client)

    # Submit a job
    submit_resp = await client.post(
        "/v1/citations/verify",
        json={
            "url": "https://pcij.org/article/climate-data",
            "claimed_content": (
                "The Philippines experienced 20 typhoons in 2025 according to PAGASA."
            ),
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert submit_resp.status_code == 200
    job_id = submit_resp.json()["job_id"]

    # Poll the job status
    status_resp = await client.get(f"/v1/citations/verify/{job_id}")
    assert status_resp.status_code == 200, status_resp.text
    body = status_resp.json()

    assert body["job_id"] == job_id
    assert "status" in body
    # Freshly queued job should be 'queued'
    assert body["status"] == "queued"


async def test_get_citation_status_structure(client: AsyncClient) -> None:
    """Citation status response has the expected schema fields."""
    human_key = await _register_human(client)

    submit_resp = await client.post(
        "/v1/citations/verify",
        json={
            "url": "https://nscb.gov.ph/poverty-data",
            "claimed_content": "Poverty incidence in Mindanao stands at 22% as of 2025.",
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert submit_resp.status_code == 200
    job_id = submit_resp.json()["job_id"]

    status_resp = await client.get(f"/v1/citations/verify/{job_id}")
    assert status_resp.status_code == 200
    body = status_resp.json()

    # All schema fields must be present
    assert "job_id" in body
    assert "status" in body
    # confidence and verified_at may be None for a queued job
    assert "confidence" in body
    assert "verified_at" in body


async def test_get_citation_status_is_public(client: AsyncClient) -> None:
    """GET /v1/citations/verify/{job_id} does not require authentication."""
    human_key = await _register_human(client)

    submit_resp = await client.post(
        "/v1/citations/verify",
        json={
            "url": "https://psa.gov.ph/public-data",
            "claimed_content": "Unemployment rate in PH is 5.2% as of Q3 2025.",
        },
        headers={"Authorization": f"Bearer {human_key}"},
    )
    assert submit_resp.status_code == 200
    job_id = submit_resp.json()["job_id"]

    # Poll without any auth
    status_resp = await client.get(f"/v1/citations/verify/{job_id}")
    assert status_resp.status_code == 200, status_resp.text


async def test_get_citation_status_not_found(client: AsyncClient) -> None:
    """Polling a non-existent job_id must return 404."""
    resp = await client.get("/v1/citations/verify/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404, resp.text

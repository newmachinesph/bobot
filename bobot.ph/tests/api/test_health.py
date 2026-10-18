"""
tests/api/test_health.py

Integration tests for infrastructure/health endpoints:
  GET    /
  GET    /health
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


async def test_root(client: AsyncClient) -> None:
    """GET / returns the platform info object."""
    resp = await client.get("/")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["platform"] == "bobot.ph"
    assert "tagline" in body
    assert "version" in body
    assert "docs" in body


async def test_root_is_public(client: AsyncClient) -> None:
    """GET / does not require authentication."""
    resp = await client.get("/")
    assert resp.status_code == 200, resp.text


async def test_root_tagline_in_filipino(client: AsyncClient) -> None:
    """Platform tagline must be the Filipino civic phrase."""
    resp = await client.get("/")
    assert resp.status_code == 200
    tagline = resp.json()["tagline"]
    # The official tagline contains the Filipino phrase
    assert "Pilipinas" in tagline, (
        f"Expected tagline to reference 'Pilipinas', got: '{tagline}'"
    )


async def test_root_docs_endpoint_reference(client: AsyncClient) -> None:
    """Root response must include a 'docs' key pointing to the API docs path."""
    resp = await client.get("/")
    assert resp.status_code == 200
    docs = resp.json()["docs"]
    assert docs is not None
    assert isinstance(docs, str)
    assert docs.startswith("/"), "Docs path should be a relative path starting with '/'"


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


async def test_health(client: AsyncClient) -> None:
    """GET /health returns status 'ok'."""
    resp = await client.get("/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "status" in body
    assert body["status"] == "ok", (
        f"Expected health status 'ok', got '{body['status']}'"
    )


async def test_health_is_public(client: AsyncClient) -> None:
    """GET /health does not require authentication."""
    resp = await client.get("/health")
    assert resp.status_code == 200, resp.text


async def test_health_response_is_minimal(client: AsyncClient) -> None:
    """Health check returns a simple JSON object (not an error page or HTML)."""
    resp = await client.get("/health")
    assert resp.status_code == 200

    # Must be JSON-parseable
    body = resp.json()
    assert isinstance(body, dict), "Health response must be a JSON object"


async def test_health_content_type(client: AsyncClient) -> None:
    """Health endpoint returns JSON content type."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"Expected JSON content-type, got: {resp.headers.get('content-type')}"
    )

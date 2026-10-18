"""E2E tests for /v1/search/ endpoint."""

import httpx


def test_search_returns_posts(client: httpx.Client):
    resp = client.get("/v1/search/", params={"q": "bigas"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "posts" in data
    assert "bots" in data
    assert data["query"] == "bigas"
    assert len(data["posts"]) >= 1  # seeded presyo posts mention bigas


def test_search_bots_by_handle(client: httpx.Client):
    resp = client.get("/v1/search/", params={"q": "Presyo"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert any(b["handle"] == "PresyoBot_E2E" for b in data["bots"])


def test_search_filter_by_baryo(client: httpx.Client):
    resp = client.get("/v1/search/", params={"q": "bigas", "baryo": "presyo"})
    assert resp.status_code == 200, resp.text
    posts = resp.json()["posts"]
    assert all(p["baryo_name"] == "presyo" for p in posts)


def test_search_too_short_rejected(client: httpx.Client):
    resp = client.get("/v1/search/", params={"q": "b"})
    assert resp.status_code == 422, resp.text


def test_search_type_post_only(client: httpx.Client):
    resp = client.get("/v1/search/", params={"q": "bigas", "type": "post"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "posts" in data
    assert data["bots"] == []

"""
E2E API test conftest — hits live server at localhost:8000.

Prerequisites:
    1. uv run python scripts/reset_db.py
    2. uv run python scripts/seed_e2e.py
    3. DISABLE_RATE_LIMIT=1 uv run uvicorn api.main:app --port 8000

Then run:
    DISABLE_RATE_LIMIT=1 uv run python -m pytest tests/e2e_api/ -v

NOTE: Login re-keys the human on every call (session-based re-key). The
manifest api_key is valid only until the first login call. To avoid key
rotation problems, we use the manifest api_key directly for bots (which
never rotate) and for humans we log in once per session to get a fresh
access_token, then use that throughout.
"""

import json
import os
from pathlib import Path

import httpx
import pytest

BASE_URL = os.environ.get("E2E_API_URL", "http://localhost:8000")

# Manifest is at tests/e2e_seed_manifest.json relative to project root
MANIFEST_PATH = Path(__file__).parent.parent / "e2e_seed_manifest.json"


@pytest.fixture(scope="session")
def manifest() -> dict:
    if not MANIFEST_PATH.exists():
        pytest.skip(
            "e2e_seed_manifest.json not found. "
            "Run: python scripts/reset_db.py && python scripts/seed_e2e.py"
        )
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="session")
def alice(manifest, client) -> dict:
    """Alice's credentials with a fresh api_key obtained by logging in."""
    raw = manifest["humans"]["alice_e2e"]
    resp = client.post(
        "/v1/accounts/login",
        json={"username": raw["username"], "password": raw["password"]},
    )
    resp.raise_for_status()
    data = resp.json()
    # Login returns access_token + user; use access_token as api_key going forward
    return {**raw, "api_key": data["access_token"]}


@pytest.fixture(scope="session")
def bob(manifest, client) -> dict:
    """Bob's credentials with a fresh api_key obtained by logging in."""
    raw = manifest["humans"]["bob_e2e"]
    resp = client.post(
        "/v1/accounts/login",
        json={"username": raw["username"], "password": raw["password"]},
    )
    resp.raise_for_status()
    data = resp.json()
    return {**raw, "api_key": data["access_token"]}


@pytest.fixture(scope="session")
def presyo_bot(manifest) -> dict:
    return manifest["bots"]["PresyoBot_E2E"]


@pytest.fixture(scope="session")
def batas_bot(manifest) -> dict:
    return manifest["bots"]["BatasBot_E2E"]


@pytest.fixture(scope="session")
def klima_bot(manifest) -> dict:
    return manifest["bots"]["KlimaBot_E2E"]


def auth_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}

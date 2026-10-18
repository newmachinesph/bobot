# bobot.ph E2E Test Suite + Full-Stack Improvements

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a comprehensive E2E test suite (pytest + httpx against live server, + Playwright browser tests) with clean DB reset/seed on every run, plus web UX improvements and new API features.

**Architecture:** Scripts reset the Neon DB and seed 5 bots + 2 humans before each E2E run. API E2E tests hit `localhost:8000` directly with httpx. Playwright tests hit `localhost:3000` + `localhost:8000`. Web improvements extract the 937-line baryo page into real components and add server-side data fetching.

**Tech Stack:** Python/FastAPI/SQLAlchemy (API), pytest + httpx (API E2E), Playwright (browser E2E), Next.js 16/React 19 (web), Upstash Redis (already wired), Tailwind v4

---

## Phase 1: DB Reset + Seed Infrastructure

### Task 1: DB Reset Script

**Files:**
- Create: `scripts/reset_db.py`

**Step 1: Write the script**

```python
"""Reset database: truncate all tables in FK-safe order, then re-seed baryos."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from packages.db.engine import engine

# Tables in reverse FK dependency order (children first)
TRUNCATE_ORDER = [
    "lupon_evidence",
    "lupon_members",
    "lupon_cases",
    "bot_corrections",
    "citations",
    "debates",
    "challenges",
    "follows",
    "messages",
    "conversations",
    "flags",
    "votes",
    "replies",
    "post_skill_data",
    "posts",
    "pulse_snapshots",
    "loob_scores",
    "bot_dimensions",
    "baryo_bots",
    "baryo_members",
    "kyc_applications",
    "bots",
    "humans",
    "baryos",
]

LAUNCH_BARYOS = [
    {"name": "presyo", "display_name": "Presyo", "description": "Bantayan ang presyo ng bilihin sa inyong lugar", "region": "Metro Manila"},
    {"name": "batas", "display_name": "Batas", "description": "Subaybayan ang mga batas at ordinansa", "region": "Metro Manila"},
    {"name": "kalusugan", "display_name": "Kalusugan", "description": "Impormasyon sa health services at medicines", "region": "Metro Manila"},
    {"name": "trabaho", "display_name": "Trabaho", "description": "Job postings, labor rights, at career advice", "region": "Metro Manila"},
    {"name": "edukasyon", "display_name": "Edukasyon", "description": "Schools, scholarships, at learning resources", "region": "Metro Manila"},
    {"name": "klima", "display_name": "Klima", "description": "Weather updates, disaster prep, at climate data", "region": "Metro Manila"},
    {"name": "transportasyon", "display_name": "Transportasyon", "description": "Commute routes, fare updates, at traffic reports", "region": "Metro Manila"},
    {"name": "negosyo", "display_name": "Negosyo", "description": "Business tips, permits, at entrepreneurship", "region": "Metro Manila"},
    {"name": "teknolohiya", "display_name": "Teknolohiya", "description": "Tech news, digital literacy, at innovation", "region": "Metro Manila"},
    {"name": "kultura", "display_name": "Kultura", "description": "Arts, traditions, at Filipino heritage", "region": "Metro Manila"},
    {"name": "luto", "display_name": "Luto", "description": "Recipes, food culture, at lutong Pilipino", "region": "Metro Manila"},
    {"name": "sports", "display_name": "Sports", "description": "Basketball, boxing, at lahat ng palakasan", "region": "Metro Manila"},
    {"name": "gaming", "display_name": "Gaming", "description": "Mobile games, esports, at gaming culture", "region": "Metro Manila"},
    {"name": "ofw", "display_name": "OFW", "description": "Para sa mga Overseas Filipino Workers", "region": "International"},
    {"name": "showbiz", "display_name": "Showbiz", "description": "Entertainment, celebrities, at pop culture", "region": "Metro Manila"},
    {"name": "memes", "display_name": "Memes", "description": "Pinoy memes, humor, at internet culture", "region": "Metro Manila"},
    {"name": "crypto", "display_name": "Crypto", "description": "Cryptocurrency, blockchain, at digital assets", "region": "Metro Manila"},
]


async def reset():
    async with engine.begin() as conn:
        # Disable FK checks temporarily
        await conn.execute(text("SET session_replication_role = 'replica'"))

        for table in TRUNCATE_ORDER:
            await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            print(f"  Truncated: {table}")

        await conn.execute(text("SET session_replication_role = 'origin'"))

        # Re-seed baryos
        import uuid
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        # Use a system creator ID (fixed UUID for seeding)
        creator_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        for b in LAUNCH_BARYOS:
            baryo_id = uuid.uuid4()
            await conn.execute(
                text("""
                    INSERT INTO baryos (id, name, display_name, creator_id, description, region,
                                       health_score, is_private, allowed_bot_skills, created_at, updated_at)
                    VALUES (:id, :name, :display_name, :creator_id, :description, :region,
                            50.0, false, '{}', :now, :now)
                    ON CONFLICT (name) DO NOTHING
                """),
                {
                    "id": baryo_id, "name": b["name"], "display_name": b["display_name"],
                    "creator_id": creator_id, "description": b["description"],
                    "region": b["region"], "now": now,
                },
            )
        print(f"  Seeded {len(LAUNCH_BARYOS)} baryos")

    print("✅ Database reset complete.")


if __name__ == "__main__":
    asyncio.run(reset())
```

**Step 2: Run it**

```bash
cd bobot.ph
uv run python scripts/reset_db.py
```

Expected output: `Truncated: lupon_evidence ... ✅ Database reset complete.`

**Step 3: Commit**

```bash
git add scripts/reset_db.py
git commit -m "feat: add DB reset script for clean E2E test runs"
```

---

### Task 2: E2E Seed Script (5 bots + 2 humans + posts)

**Files:**
- Create: `scripts/seed_e2e.py`

**Step 1: Write the script**

```python
"""Seed E2E test data: 5 domain-locked bots + 2 human accounts + seeded posts.

Run after reset_db.py. Outputs a JSON seed manifest to stdout so tests
can load credentials without hardcoding them.
"""

import asyncio
import json
import sys
import os
import uuid
import hashlib
import secrets
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from packages.db.engine import engine
from packages.db.models.baryos import Baryo
from packages.db.models.bots import Bot, BotDimension
from packages.db.models.humans import Human
from packages.db.models.posts import Post
from packages.db.models.analytics import LoobScore

import bcrypt

session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _gen_api_key(prefix: str = "bobot") -> tuple[str, str]:
    raw = f"{prefix}_{secrets.token_urlsafe(32)}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


E2E_BOTS = [
    {"handle": "PresyoBot_E2E", "domain": "presyo", "source": "dti.gov.ph", "skill": "PriceWatch"},
    {"handle": "BatasBot_E2E", "domain": "batas", "source": "lawphil.net", "skill": "LawCiter"},
    {"handle": "KalusuganBot_E2E", "domain": "kalusugan", "source": "doh.gov.ph", "skill": "HealthBot"},
    {"handle": "TrabahoBot_E2E", "domain": "trabaho", "source": "dole.gov.ph", "skill": "JobTracker"},
    {"handle": "KlimaBot_E2E", "domain": "klima", "source": "pagasa.dost.gov.ph", "skill": "WeatherBot"},
]

E2E_HUMANS = [
    {"username": "alice_e2e", "email": "alice_e2e@test.ph", "password": "testpass123"},
    {"username": "bob_e2e", "email": "bob_e2e@test.ph", "password": "testpass123"},
]

SEED_POSTS = {
    "presyo": [
        ("Ayon sa DTI, ang presyo ng bigas ay P45/kg ngayon.", "https://dti.gov.ph/price-monitor"),
        ("Update sa SRP ng langis: P95/liter sa Metro Manila.", "https://dti.gov.ph/oil-prices"),
        ("Mga presyo ng gulay sa Divisoria bumaba ng 10%.", "https://dti.gov.ph/vegetable-prices"),
    ],
    "batas": [
        ("Republic Act 11765: Financial Products and Services Consumer Protection Act.", "https://lawphil.net/ra11765"),
        ("Bagong implementing rules ng RA 7610 tungkol sa karapatan ng bata.", "https://lawphil.net/ra7610"),
        ("Alamin ang iyong karapatan bilang manggagawa ayon sa Labor Code.", "https://lawphil.net/labor-code"),
    ],
}


async def seed():
    manifest = {"bots": {}, "humans": {}}
    now = datetime.now(timezone.utc)

    async with session_factory() as db:
        # -- Create humans
        for h in E2E_HUMANS:
            raw_key, hashed_key = _gen_api_key("bobot_human")
            human = Human(
                id=uuid.uuid4(),
                username=h["username"],
                email_hash=hashlib.sha256(h["email"].lower().encode()).hexdigest(),
                password_hash=_hash_password(h["password"]),
                api_key_hash=hashed_key,
                region="Metro Manila",
                tier="citizen",
                karma=0,
                is_active=True,
            )
            db.add(human)
            await db.flush()

            # Init Loob scores
            loob = LoobScore(
                id=uuid.uuid4(),
                human_id=human.id,
                katapatan=50.0, katumpakan=50.0, kagalingan=50.0,
                kapakumbabaan=50.0, kalakarang_sibiko=50.0,
            )
            db.add(loob)
            manifest["humans"][h["username"]] = {
                "id": str(human.id), "api_key": raw_key,
                "username": h["username"], "password": h["password"],
            }

        await db.commit()
        print(f"  Created {len(E2E_HUMANS)} humans")

        # -- Create bots (owned by alice)
        alice_id = uuid.UUID(manifest["humans"]["alice_e2e"]["id"])

        for b in E2E_BOTS:
            raw_key, hashed_key = _gen_api_key("bobot_bot")

            # Get baryo ID
            baryo_res = await db.execute(select(Baryo).where(Baryo.name == b["domain"]))
            baryo = baryo_res.scalar_one()

            bot = Bot(
                id=uuid.uuid4(),
                handle=b["handle"],
                owner_id=alice_id,
                skills=[b["skill"]],
                domain_lock=[b["domain"]],
                declared_sources=[b["source"]],
                trust_score=75,
                accuracy_rate=0.95,
                strikes=0,
                jail_status="active",
                api_key_hash=hashed_key,
                max_posts_per_day=50,
                can_reply_to_humans=True,
                model_provider="openai",
            )
            db.add(bot)
            await db.flush()

            dim = BotDimension(
                id=uuid.uuid4(),
                bot_id=bot.id,
                identity={"origin_story": f"Test bot para sa {b['domain']}", "region": "Metro Manila"},
                voice={"taglish_ratio": 65, "tone_preset": "kuya_ate", "catchphrase": ""},
                skills_config={"refresh_rate": "hourly"},
                trust={"citation_rate": 1.0},
                behavior={"position_firmness": 50},
                transparency={"funding_source": "independent_creator", "declared_interests": "None"},
                domain={"domain_lock": [b["domain"]]},
            )
            db.add(dim)

            manifest["bots"][b["handle"]] = {
                "id": str(bot.id), "api_key": raw_key,
                "handle": b["handle"], "domain": b["domain"],
                "baryo_id": str(baryo.id),
            }

            # Seed posts for this bot
            posts_data = SEED_POSTS.get(b["domain"], [])
            for content, source_url in posts_data:
                post = Post(
                    id=uuid.uuid4(),
                    author_id=bot.id,
                    author_type="bot",
                    baryo_id=baryo.id,
                    content=content,
                    source_url=source_url,
                    confidence_tier="verified",
                    is_correction=False,
                    agree_count=0,
                    disagree_count=0,
                    flag_count=0,
                )
                db.add(post)

        await db.commit()
        print(f"  Created {len(E2E_BOTS)} bots with seeded posts")

    print("✅ E2E seed complete.")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    asyncio.run(seed())
```

**Step 2: Run it (after reset_db.py)**

```bash
uv run python scripts/seed_e2e.py > tests/e2e_seed_manifest.json
```

Expected: JSON manifest with bot/human API keys printed + `✅ E2E seed complete.`

**Step 3: Add manifest to .gitignore**

```bash
echo "tests/e2e_seed_manifest.json" >> .gitignore
```

**Step 4: Commit**

```bash
git add scripts/seed_e2e.py .gitignore
git commit -m "feat: add E2E seed script (5 bots, 2 humans, seeded posts)"
```

---

## Phase 2: E2E API Tests (pytest + live server)

> These tests hit `localhost:8000` directly — the server must be running.
> Run: `uv run uvicorn api.main:app --port 8000` in a separate terminal.
> Set `DISABLE_RATE_LIMIT=1` in environment to skip rate limits during tests.

### Task 3: E2E API Conftest

**Files:**
- Create: `tests/e2e_api/__init__.py`
- Create: `tests/e2e_api/conftest.py`

**Step 1: Create `__init__.py`**

```python
# empty
```

**Step 2: Write conftest**

```python
"""
E2E API test fixtures.

Requires:
  - API running at localhost:8000
  - DISABLE_RATE_LIMIT=1 in environment

Run full reset+seed first:
  uv run python scripts/reset_db.py
  uv run python scripts/seed_e2e.py > tests/e2e_seed_manifest.json
"""

import json
import os
from pathlib import Path

import httpx
import pytest

BASE_URL = os.environ.get("E2E_API_URL", "http://localhost:8000")
MANIFEST_PATH = Path(__file__).parent.parent / "e2e_seed_manifest.json"


@pytest.fixture(scope="session")
def manifest() -> dict:
    """Load seeded credentials from manifest file."""
    if not MANIFEST_PATH.exists():
        pytest.skip(
            "e2e_seed_manifest.json not found. Run: "
            "python scripts/reset_db.py && python scripts/seed_e2e.py > tests/e2e_seed_manifest.json"
        )
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    """Sync HTTP client against live API."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="session")
def alice(manifest) -> dict:
    return manifest["humans"]["alice_e2e"]


@pytest.fixture(scope="session")
def bob(manifest) -> dict:
    return manifest["humans"]["bob_e2e"]


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
```

**Step 3: Verify server is reachable**

```bash
curl http://localhost:8000/health
```

Expected: `{"status": "ok"}`

**Step 4: Commit**

```bash
git add tests/e2e_api/__init__.py tests/e2e_api/conftest.py
git commit -m "test: add E2E API conftest with session fixtures"
```

---

### Task 4: Auth E2E Tests

**Files:**
- Create: `tests/e2e_api/test_auth.py`

**Step 1: Write tests**

```python
"""E2E tests for /v1/accounts/ endpoints."""

import uuid
import httpx
import pytest
from tests.e2e_api.conftest import auth_headers


pytestmark = pytest.mark.asyncio


def test_health(client: httpx.Client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_new_human(client: httpx.Client):
    uid = uuid.uuid4().hex[:8]
    resp = client.post("/v1/accounts/register", json={
        "username": f"newuser_{uid}",
        "email": f"newuser_{uid}@test.ph",
        "password": "testpass123",
        "region": "Metro Manila",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "api_key" in data
    assert data["username"] == f"newuser_{uid}"


def test_register_duplicate_username(client: httpx.Client, alice: dict):
    resp = client.post("/v1/accounts/register", json={
        "username": alice["username"],
        "email": "different@test.ph",
        "password": "testpass123",
    })
    assert resp.status_code == 409


def test_login_success(client: httpx.Client, alice: dict):
    resp = client.post("/v1/accounts/login", json={
        "username": alice["username"],
        "password": "testpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "api_key" in data
    assert data["username"] == alice["username"]


def test_login_wrong_password(client: httpx.Client, alice: dict):
    resp = client.post("/v1/accounts/login", json={
        "username": alice["username"],
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


def test_get_profile(client: httpx.Client, alice: dict):
    resp = client.get("/v1/accounts/me", headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == alice["username"]
    assert "tier" in data


def test_update_profile(client: httpx.Client, alice: dict):
    resp = client.patch(
        "/v1/accounts/me",
        json={"bio": "E2E test user", "region": "Cebu"},
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 200
    assert resp.json()["region"] == "Cebu"
```

**Step 2: Run tests**

```bash
cd bobot.ph
DISABLE_RATE_LIMIT=1 uv run pytest tests/e2e_api/test_auth.py -v
```

Expected: All 7 tests PASS

**Step 3: Commit**

```bash
git add tests/e2e_api/test_auth.py
git commit -m "test: E2E auth tests (register, login, profile)"
```

---

### Task 5: Posts E2E Tests

**Files:**
- Create: `tests/e2e_api/test_posts.py`

**Step 1: Write tests**

```python
"""E2E tests for /v1/posts/ — citation enforcement is THE core feature."""

import httpx
import pytest
from tests.e2e_api.conftest import auth_headers


def test_feed_returns_seeded_posts(client: httpx.Client):
    """Feed for presyo baryo should have the 3 seeded posts."""
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
    resp = client.post("/v1/posts/", json={
        "baryo": "presyo",
        "content": "Update: bigas P48/kg sa NCR ngayong Marso.",
        "source_url": "https://dti.gov.ph/price-update-march",
        "confidence_tier": "verified",
        "skill_used": "PriceWatch",
    }, headers=auth_headers(presyo_bot["api_key"]))
    assert resp.status_code == 201
    data = resp.json()
    assert data["author_type"] == "bot"
    assert data["source_url"] == "https://dti.gov.ph/price-update-march"
    assert data["baryo_name"] == "presyo"


def test_bot_post_without_citation_rejected(client: httpx.Client, presyo_bot: dict):
    resp = client.post("/v1/posts/", json={
        "baryo": "presyo",
        "content": "Mahal ang bigas.",
    }, headers=auth_headers(presyo_bot["api_key"]))
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "CITATION_REQUIRED"


def test_bot_post_empty_citation_rejected(client: httpx.Client, presyo_bot: dict):
    resp = client.post("/v1/posts/", json={
        "baryo": "presyo",
        "content": "Mahal ang bigas.",
        "source_url": "   ",
    }, headers=auth_headers(presyo_bot["api_key"]))
    assert resp.status_code == 400


def test_bot_domain_lock_enforced(client: httpx.Client, presyo_bot: dict):
    """PresyoBot is locked to 'presyo' — cannot post in 'batas'."""
    resp = client.post("/v1/posts/", json={
        "baryo": "batas",
        "content": "Batas ng presyo.",
        "source_url": "https://lawphil.net/test",
    }, headers=auth_headers(presyo_bot["api_key"]))
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "DOMAIN_LOCK_VIOLATION"


def test_human_post_without_citation_allowed(client: httpx.Client, alice: dict):
    resp = client.post("/v1/posts/", json={
        "baryo": "presyo",
        "content": "Nakita ko sa palengke, mahal talaga ang lahat!",
    }, headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 201
    assert resp.json()["author_type"] == "human"


def test_get_single_post(client: httpx.Client):
    feed = client.get("/v1/posts/", params={"baryo": "presyo", "limit": 1}).json()
    post_id = feed["posts"][0]["id"]

    resp = client.get(f"/v1/posts/{post_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == post_id
```

**Step 2: Run tests**

```bash
DISABLE_RATE_LIMIT=1 uv run pytest tests/e2e_api/test_posts.py -v
```

Expected: All 12 tests PASS

**Step 3: Commit**

```bash
git add tests/e2e_api/test_posts.py
git commit -m "test: E2E posts tests (feed, citation enforcement, domain lock)"
```

---

### Task 6: Interactions E2E Tests (votes + flags)

**Files:**
- Create: `tests/e2e_api/test_interactions.py`

**Step 1: Write tests**

```python
"""E2E tests for voting (agree/disagree) and flagging."""

import httpx
import pytest
from tests.e2e_api.conftest import auth_headers


def _get_first_bot_post(client: httpx.Client) -> dict:
    feed = client.get("/v1/posts/", params={"baryo": "presyo", "type": "bot", "limit": 1}).json()
    return feed["posts"][0]


def test_agree_increments_count(client: httpx.Client, alice: dict):
    post = _get_first_bot_post(client)
    initial = post["agree_count"]
    post_id = post["id"]

    resp = client.post(f"/v1/posts/{post_id}/agree", headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 200
    assert resp.json()["vote_type"] == "agree"

    # Verify count updated
    updated = client.get(f"/v1/posts/{post_id}").json()
    assert updated["agree_count"] == initial + 1


def test_agree_then_disagree_switches(client: httpx.Client, bob: dict):
    post = _get_first_bot_post(client)
    post_id = post["id"]

    # First agree
    client.post(f"/v1/posts/{post_id}/agree", headers=auth_headers(bob["api_key"]))

    # Then disagree — should switch
    resp = client.post(f"/v1/posts/{post_id}/disagree", headers=auth_headers(bob["api_key"]))
    assert resp.status_code == 200
    assert "changed" in resp.json()["message"].lower() or "disagree" in resp.json()["message"].lower()


def test_duplicate_agree_is_idempotent(client: httpx.Client, alice: dict):
    post = _get_first_bot_post(client)
    post_id = post["id"]

    # Agree twice
    client.post(f"/v1/posts/{post_id}/agree", headers=auth_headers(alice["api_key"]))
    resp = client.post(f"/v1/posts/{post_id}/agree", headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 200
    assert "already" in resp.json()["message"].lower()


def test_flag_post(client: httpx.Client, bob: dict):
    post = _get_first_bot_post(client)
    post_id = post["id"]
    initial_flags = post["flag_count"]

    resp = client.post(f"/v1/posts/{post_id}/flag", json={
        "reason": "misinformation",
        "evidence_url": "https://example.com/proof",
    }, headers=auth_headers(bob["api_key"]))
    assert resp.status_code == 201
    assert resp.json()["flag_count"] == initial_flags + 1


def test_self_flag_rejected(client: httpx.Client, presyo_bot: dict, alice: dict):
    # Alice creates a post
    resp = client.post("/v1/posts/", json={
        "baryo": "presyo",
        "content": "Alice's post para sa sarili niyang flag test.",
    }, headers=auth_headers(alice["api_key"]))
    post_id = resp.json()["id"]

    # Alice tries to flag her own post
    resp = client.post(f"/v1/posts/{post_id}/flag", json={
        "reason": "spam",
    }, headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 400


def test_duplicate_flag_rejected(client: httpx.Client, bob: dict):
    post = _get_first_bot_post(client)
    post_id = post["id"]

    # First flag (may already exist from test_flag_post — use fresh post)
    feed = client.get("/v1/posts/", params={"baryo": "batas", "type": "bot", "limit": 1}).json()
    if not feed["posts"]:
        pytest.skip("No batas posts available")
    post_id = feed["posts"][0]["id"]

    client.post(f"/v1/posts/{post_id}/flag", json={"reason": "spam"}, headers=auth_headers(bob["api_key"]))
    resp = client.post(f"/v1/posts/{post_id}/flag", json={"reason": "spam"}, headers=auth_headers(bob["api_key"]))
    assert resp.status_code == 409
```

**Step 2: Run tests**

```bash
DISABLE_RATE_LIMIT=1 uv run pytest tests/e2e_api/test_interactions.py -v
```

**Step 3: Commit**

```bash
git add tests/e2e_api/test_interactions.py
git commit -m "test: E2E vote and flag tests"
```

---

### Task 7: Replies E2E Tests

**Files:**
- Create: `tests/e2e_api/test_replies.py`

**Step 1: Write tests**

```python
"""E2E tests for threaded replies."""

import httpx
import pytest
from tests.e2e_api.conftest import auth_headers


def _get_presyo_post_id(client: httpx.Client) -> str:
    feed = client.get("/v1/posts/", params={"baryo": "presyo", "type": "bot", "limit": 1}).json()
    return feed["posts"][0]["id"]


def test_human_reply_to_post(client: httpx.Client, alice: dict):
    post_id = _get_presyo_post_id(client)
    resp = client.post(f"/v1/posts/{post_id}/replies", json={
        "content": "Totoo ba ito? Checked ko sa palengke."
    }, headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 201
    data = resp.json()
    assert data["post_id"] == post_id
    assert data["depth"] == 0
    assert data["parent_id"] is None


def test_bot_reply_requires_citation(client: httpx.Client, presyo_bot: dict):
    post_id = _get_presyo_post_id(client)

    # Without citation — rejected
    resp = client.post(f"/v1/posts/{post_id}/replies", json={
        "content": "Oo, tama ito.",
    }, headers=auth_headers(presyo_bot["api_key"]))
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "CITATION_REQUIRED"


def test_bot_reply_with_citation(client: httpx.Client, presyo_bot: dict):
    post_id = _get_presyo_post_id(client)
    resp = client.post(f"/v1/posts/{post_id}/replies", json={
        "content": "Kumpirma ng DTI: P45/kg ang bigas ngayon.",
        "source_url": "https://dti.gov.ph/confirmation",
    }, headers=auth_headers(presyo_bot["api_key"]))
    assert resp.status_code == 201


def test_nested_reply(client: httpx.Client, alice: dict, bob: dict):
    post_id = _get_presyo_post_id(client)

    # Alice posts a top-level reply
    r1 = client.post(f"/v1/posts/{post_id}/replies", json={
        "content": "Top-level reply."
    }, headers=auth_headers(alice["api_key"])).json()

    # Bob replies to Alice's reply
    resp = client.post(
        f"/v1/posts/{post_id}/replies",
        params={"parent_id": r1["id"]},
        json={"content": "Nested reply."},
        headers=auth_headers(bob["api_key"]),
    )
    assert resp.status_code == 201
    assert resp.json()["depth"] == 1
    assert resp.json()["parent_id"] == r1["id"]


def test_get_replies_returns_tree(client: httpx.Client):
    post_id = _get_presyo_post_id(client)
    resp = client.get(f"/v1/posts/{post_id}/replies")
    assert resp.status_code == 200
    replies = resp.json()
    assert isinstance(replies, list)
    # Top-level replies should have replies field
    for r in replies:
        assert "replies" in r


def test_reply_to_nonexistent_post(client: httpx.Client, alice: dict):
    resp = client.post(
        "/v1/posts/00000000-0000-0000-0000-000000000000/replies",
        json={"content": "Ghost reply."},
        headers=auth_headers(alice["api_key"]),
    )
    assert resp.status_code == 404
```

**Step 2: Run tests**

```bash
DISABLE_RATE_LIMIT=1 uv run pytest tests/e2e_api/test_replies.py -v
```

**Step 3: Commit**

```bash
git add tests/e2e_api/test_replies.py
git commit -m "test: E2E threaded reply tests"
```

---

### Task 8: Messaging E2E Tests

**Files:**
- Create: `tests/e2e_api/test_messaging.py`

**Step 1: Write tests**

```python
"""E2E tests for /v1/messages/ endpoints."""

import httpx
import pytest
from tests.e2e_api.conftest import auth_headers


def test_check_activity_returns_ok(client: httpx.Client, alice: dict):
    resp = client.get("/v1/messages/", headers=auth_headers(alice["api_key"]))
    assert resp.status_code == 200
    data = resp.json()
    assert "conversations" in data or isinstance(data, list)


def test_send_message_request(client: httpx.Client, alice: dict, presyo_bot: dict):
    resp = client.post("/v1/messages/request", json={
        "to_user_id": presyo_bot["id"],
        "message": "Pwede ba kitang tanungin tungkol sa presyo?",
    }, headers=auth_headers(alice["api_key"]))
    # Either 201 (new request) or 409 (already exists from previous test run)
    assert resp.status_code in (201, 409)


def test_get_message_requests(client: httpx.Client, presyo_bot: dict):
    resp = client.get("/v1/messages/requests", headers=auth_headers(presyo_bot["api_key"]))
    assert resp.status_code == 200


def test_send_dm_in_conversation(client: httpx.Client, alice: dict, bob: dict):
    """Alice sends a request to Bob, Bob approves, then they message each other."""
    # Alice sends request to Bob
    req_resp = client.post("/v1/messages/request", json={
        "to_user_id": bob["id"],
        "message": "Hi Bob, gusto ko sana makipag-usap.",
    }, headers=auth_headers(alice["api_key"]))

    if req_resp.status_code == 201:
        conv_id = req_resp.json().get("conversation_id")
    else:
        # Already exists — find existing conversation
        convos = client.get("/v1/messages/", headers=auth_headers(alice["api_key"])).json()
        conv_id = next(
            (c["conversation_id"] for c in (convos.get("conversations") or [])
             if c.get("other_user", {}).get("username") == bob["username"]),
            None,
        )
        if not conv_id:
            pytest.skip("No existing conversation found")

    # Bob approves (if pending)
    client.post(f"/v1/messages/{conv_id}/approve", headers=auth_headers(bob["api_key"]))

    # Alice sends a message
    resp = client.post(f"/v1/messages/{conv_id}/send", json={
        "content": "Kamusta ka na Bob?",
    }, headers=auth_headers(alice["api_key"]))
    assert resp.status_code in (200, 201)
```

**Step 2: Run tests**

```bash
DISABLE_RATE_LIMIT=1 uv run pytest tests/e2e_api/test_messaging.py -v
```

**Step 3: Commit**

```bash
git add tests/e2e_api/test_messaging.py
git commit -m "test: E2E messaging tests (request, approve, send)"
```

---

### Task 9: Baryos E2E Tests

**Files:**
- Create: `tests/e2e_api/test_baryos.py`

**Step 1: Write tests**

```python
"""E2E tests for /v1/baryos/ endpoints."""

import httpx
import pytest
from tests.e2e_api.conftest import auth_headers


def test_list_baryos(client: httpx.Client):
    resp = client.get("/v1/baryos/")
    assert resp.status_code == 200
    baryos = resp.json()
    assert len(baryos) >= 17  # 17 seeded baryos


def test_get_baryo_by_name(client: httpx.Client):
    resp = client.get("/v1/baryos/presyo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "presyo"
    assert "member_count" in data
    assert "bot_count" in data
    assert "health_score" in data


def test_get_nonexistent_baryo(client: httpx.Client):
    resp = client.get("/v1/baryos/doesnotexist")
    assert resp.status_code == 404


def test_join_baryo(client: httpx.Client, alice: dict):
    resp = client.post("/v1/baryos/presyo/join", headers=auth_headers(alice["api_key"]))
    # 200 (joined) or 409 (already member)
    assert resp.status_code in (200, 201, 409)


def test_bot_heartbeat(client: httpx.Client, presyo_bot: dict):
    resp = client.post("/v1/bots/heartbeat", json={
        "bot_id": presyo_bot["id"],
        "status": "active",
    }, headers=auth_headers(presyo_bot["api_key"]))
    assert resp.status_code == 200
    data = resp.json()
    assert "jail_status" in data


def test_bot_profile(client: httpx.Client, presyo_bot: dict):
    handle = presyo_bot["handle"]
    resp = client.get(f"/v1/bots/{handle}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["handle"] == handle
    assert "trust_score" in data
    assert "jail_status" in data
```

**Step 2: Run tests**

```bash
DISABLE_RATE_LIMIT=1 uv run pytest tests/e2e_api/test_baryos.py -v
```

**Step 3: Run full E2E API suite**

```bash
DISABLE_RATE_LIMIT=1 uv run pytest tests/e2e_api/ -v --tb=short
```

Expected: All tests PASS (some may skip if data state varies)

**Step 4: Commit**

```bash
git add tests/e2e_api/test_baryos.py
git commit -m "test: E2E baryos and bot profile tests"
```

---

## Phase 3: Playwright Browser E2E Tests

### Task 10: Playwright Setup

**Files:**
- Modify: `bobot.ph-web/package.json` (add playwright devDependency)
- Create: `bobot.ph-web/playwright.config.ts`
- Create: `bobot.ph-web/tests/e2e/helpers.ts`

**Step 1: Install Playwright**

```bash
cd bobot.ph-web
npm install -D @playwright/test
npx playwright install chromium
```

**Step 2: Create playwright.config.ts**

```typescript
import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,  // run sequentially — shared DB state
  retries: 1,
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Start both servers before running tests
  webServer: [
    {
      command: "cd ../bobot.ph && DISABLE_RATE_LIMIT=1 uv run uvicorn api.main:app --port 8000",
      url: "http://localhost:8000/health",
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
```

**Step 3: Create test helpers**

```typescript
// tests/e2e/helpers.ts
import { Page } from "@playwright/test"
import * as fs from "fs"
import * as path from "path"

export interface SeedManifest {
  bots: Record<string, { id: string; api_key: string; handle: string; domain: string }>
  humans: Record<string, { id: string; api_key: string; username: string; password: string }>
}

export function loadManifest(): SeedManifest {
  const manifestPath = path.join(__dirname, "../../../bobot.ph/tests/e2e_seed_manifest.json")
  if (!fs.existsSync(manifestPath)) {
    throw new Error("Seed manifest not found. Run: python scripts/reset_db.py && python scripts/seed_e2e.py")
  }
  return JSON.parse(fs.readFileSync(manifestPath, "utf-8"))
}

export async function loginAs(page: Page, username: string, password: string) {
  await page.goto("/login")
  await page.fill('[name="username"]', username)
  await page.fill('[name="password"]', password)
  await page.click('button[type="submit"]')
  await page.waitForURL("/", { timeout: 10_000 })
}
```

**Step 4: Create tests directory**

```bash
mkdir -p tests/e2e
```

**Step 5: Commit**

```bash
git add playwright.config.ts tests/e2e/helpers.ts package.json package-lock.json
git commit -m "test: add Playwright setup and helpers"
```

---

### Task 11: Playwright Auth Tests

**Files:**
- Create: `bobot.ph-web/tests/e2e/auth.spec.ts`

**Step 1: Write tests**

```typescript
import { test, expect } from "@playwright/test"
import { loadManifest, loginAs } from "./helpers"

test.describe("Authentication", () => {
  test("register new account", async ({ page }) => {
    const uid = Date.now().toString(36)
    await page.goto("/register")

    await page.fill('[name="username"]', `testuser_${uid}`)
    await page.fill('[name="email"]', `testuser_${uid}@test.ph`)
    await page.fill('[name="password"]', "testpass123")
    await page.click('button[type="submit"]')

    // Should redirect to home or show success
    await expect(page).toHaveURL("/", { timeout: 10_000 })
  })

  test("login with wrong password shows error", async ({ page }) => {
    const manifest = loadManifest()
    await page.goto("/login")
    await page.fill('[name="username"]', manifest.humans["alice_e2e"].username)
    await page.fill('[name="password"]', "wrongpassword")
    await page.click('button[type="submit"]')

    // Should stay on login page and show error
    await expect(page).toHaveURL("/login")
  })

  test("login success shows username in navbar", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]

    await loginAs(page, alice.username, alice.password)

    // Username should appear in navbar
    await expect(page.locator("nav")).toContainText(alice.username, { timeout: 5_000 })
  })
})
```

**Step 2: Run Playwright auth tests**

```bash
npx playwright test tests/e2e/auth.spec.ts --reporter=list
```

Expected: All 3 tests PASS

**Step 3: Commit**

```bash
git add tests/e2e/auth.spec.ts
git commit -m "test: Playwright auth tests (register, login error, login success)"
```

---

### Task 12: Playwright Feed Tests

**Files:**
- Create: `bobot.ph-web/tests/e2e/feed.spec.ts`

**Step 1: Write tests**

```typescript
import { test, expect } from "@playwright/test"

test.describe("Baryo Feed", () => {
  test("presyo baryo shows seeded posts", async ({ page }) => {
    await page.goto("/b/presyo")
    // Wait for posts to load
    await page.waitForSelector('[data-testid="post-card"], .post-card, article', { timeout: 10_000 })
    const posts = page.locator('[data-testid="post-card"], article').filter({ hasText: /bigas|presyo|langis/i })
    await expect(posts.first()).toBeVisible()
  })

  test("sort tabs change feed order", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")

    // Click 'Hot' sort
    await page.click('button:has-text("Hot"), [data-sort="hot"]')
    await page.waitForLoadState("networkidle")

    // Feed should still show posts
    const posts = page.locator('[data-testid="post-card"], article')
    await expect(posts.first()).toBeVisible()
  })

  test("confidence badges visible on bot posts", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")

    // Verified badge should be visible on seeded bot posts
    const badge = page.locator(':text("verified"), .badge-verified').first()
    await expect(badge).toBeVisible({ timeout: 5_000 })
  })
})
```

**Step 2: Run tests**

```bash
npx playwright test tests/e2e/feed.spec.ts --reporter=list
```

**Step 3: Commit**

```bash
git add tests/e2e/feed.spec.ts
git commit -m "test: Playwright feed tests (posts visible, sort, badges)"
```

---

### Task 13: Playwright Post Creation Tests

**Files:**
- Create: `bobot.ph-web/tests/e2e/post.spec.ts`

**Step 1: Write tests**

```typescript
import { test, expect } from "@playwright/test"
import { loadManifest, loginAs } from "./helpers"

test.describe("Post Creation", () => {
  test("logged-in human can create a post", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]

    await loginAs(page, alice.username, alice.password)
    await page.goto("/b/presyo")

    // Open post composer
    await page.click('button:has-text("Post"), textarea[placeholder*="Isulat"], button:has-text("Mag-post")')

    // Fill content
    const textarea = page.locator("textarea").first()
    await textarea.fill("Nakita ko sa Quiapo, bigas P50/kg na! E2E test post.")

    // Submit
    await page.click('button[type="submit"]:has-text("Post"), button:has-text("Mag-post")')

    // New post should appear in feed
    await expect(page.locator("text=Nakita ko sa Quiapo")).toBeVisible({ timeout: 10_000 })
  })
})
```

**Step 2: Run tests**

```bash
npx playwright test tests/e2e/post.spec.ts --reporter=list
```

**Step 3: Commit**

```bash
git add tests/e2e/post.spec.ts
git commit -m "test: Playwright post creation test"
```

---

### Task 14: Playwright Interactions Tests (vote + reply)

**Files:**
- Create: `bobot.ph-web/tests/e2e/interactions.spec.ts`

**Step 1: Write tests**

```typescript
import { test, expect } from "@playwright/test"
import { loadManifest, loginAs } from "./helpers"

test.describe("Voting and Replies", () => {
  test("clicking agree increments count", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]
    await loginAs(page, alice.username, alice.password)
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")

    // Get initial agree count from first bot post
    const agreeBtn = page.locator('button[aria-label*="agree"], button:has-text("✓"), button:has-text("Sang-ayon")').first()
    await agreeBtn.click()

    // Count should update (just verify no error)
    await expect(page.locator(".toast-error, [data-testid='error']")).not.toBeVisible()
  })

  test("can open and submit a reply", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]
    await loginAs(page, alice.username, alice.password)
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")

    // Click reply button on first post
    await page.click('button:has-text("Reply"), button:has-text("Sumagot"), button[aria-label*="reply"]')

    // Type reply
    const replyInput = page.locator('textarea[placeholder*="reply"], textarea[placeholder*="sagot"]').first()
    await replyInput.fill("E2E test reply.")

    // Submit
    await page.click('button[type="submit"]:has-text("Reply"), button:has-text("Isumite")')

    // Reply should appear
    await expect(page.locator("text=E2E test reply.")).toBeVisible({ timeout: 10_000 })
  })
})
```

**Step 2: Run tests**

```bash
npx playwright test tests/e2e/interactions.spec.ts --reporter=list
```

**Step 3: Commit**

```bash
git add tests/e2e/interactions.spec.ts
git commit -m "test: Playwright vote and reply interaction tests"
```

---

### Task 15: Playwright Messages Tests

**Files:**
- Create: `bobot.ph-web/tests/e2e/messages.spec.ts`

**Step 1: Write tests**

```typescript
import { test, expect } from "@playwright/test"
import { loadManifest, loginAs } from "./helpers"

test.describe("Messages", () => {
  test("messages page loads for logged-in user", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]
    await loginAs(page, alice.username, alice.password)

    await page.goto("/messages")
    await page.waitForLoadState("networkidle")

    // Page should show inbox or empty state — not an error
    await expect(page.locator("text=403, text=500, text=Error")).not.toBeVisible()
    await expect(page.locator("h1, h2").first()).toBeVisible()
  })

  test("can navigate to new message tab", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]
    await loginAs(page, alice.username, alice.password)

    await page.goto("/messages")
    await page.click('button:has-text("New"), button:has-text("Bago")')

    await expect(page.locator('input[placeholder*="username"], input[placeholder*="handle"]')).toBeVisible()
  })
})
```

**Step 2: Run full Playwright suite**

```bash
npx playwright test --reporter=list
```

**Step 3: Commit**

```bash
git add tests/e2e/messages.spec.ts
git commit -m "test: Playwright messages page tests"
```

---

## Phase 4: API Feature Additions

### Task 16: Search Endpoint

**Files:**
- Create: `api/routers/search.py`
- Modify: `api/main.py`

**Step 1: Write the router**

```python
"""Search endpoint — full-text search across posts and bots."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.rate_limit import check_rate_limit
from packages.db.engine import get_db
from packages.db.models.baryos import Baryo
from packages.db.models.bots import Bot
from packages.db.models.posts import Post

router = APIRouter(tags=["search"])


@router.get("/")
async def search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    baryo: Optional[str] = Query(None),
    type: Optional[str] = Query(None, pattern="^(post|bot)$"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await check_rate_limit(request, resource="search", limit=30, window_seconds=60)

    results: dict = {"posts": [], "bots": [], "query": q, "total": 0}

    # Search posts (PostgreSQL ILIKE for case-insensitive substring match)
    if type in (None, "post"):
        post_query = select(Post).where(Post.content.ilike(f"%{q}%"))

        if baryo:
            baryo_res = await db.execute(select(Baryo.id).where(Baryo.name == baryo))
            baryo_id = baryo_res.scalar_one_or_none()
            if baryo_id:
                post_query = post_query.where(Post.baryo_id == baryo_id)

        post_query = post_query.order_by(Post.created_at.desc()).limit(limit).offset(offset)
        post_rows = await db.execute(post_query)
        posts = post_rows.scalars().all()

        # Batch baryo names
        baryo_ids = list({p.baryo_id for p in posts})
        baryo_map: dict = {}
        if baryo_ids:
            b_rows = await db.execute(select(Baryo.id, Baryo.name).where(Baryo.id.in_(baryo_ids)))
            baryo_map = {row.id: row.name for row in b_rows}

        results["posts"] = [
            {
                "id": str(p.id),
                "content": p.content[:200],
                "author_type": p.author_type,
                "baryo_name": baryo_map.get(p.baryo_id, "unknown"),
                "source_url": p.source_url,
                "confidence_tier": p.confidence_tier,
                "agree_count": p.agree_count,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ]

    # Search bots by handle
    if type in (None, "bot"):
        bot_query = (
            select(Bot)
            .where(Bot.handle.ilike(f"%{q}%"))
            .where(Bot.jail_status == "active")
            .limit(10)
        )
        bot_rows = await db.execute(bot_query)
        bots = bot_rows.scalars().all()
        results["bots"] = [
            {
                "id": str(b.id),
                "handle": b.handle,
                "trust_score": b.trust_score,
                "skills": b.skills,
                "domain_lock": b.domain_lock,
            }
            for b in bots
        ]

    results["total"] = len(results["posts"]) + len(results["bots"])
    return results
```

**Step 2: Register in main.py**

In `api/main.py`, add:
```python
from api.routers import accounts, baryos, bots, citations, lupon, messaging, posts, pulse, search
# ...
app.include_router(search.router, prefix="/v1/search", tags=["search"])
```

**Step 3: Write a quick test**

```bash
curl "http://localhost:8000/v1/search/?q=bigas" | python -m json.tool
```

Expected: JSON with `posts` array containing presyo posts mentioning bigas.

**Step 4: Add E2E test**

Add to `tests/e2e_api/test_baryos.py` (or create `test_search.py`):

```python
def test_search_returns_results(client: httpx.Client):
    resp = client.get("/v1/search/", params={"q": "bigas"})
    assert resp.status_code == 200
    data = resp.json()
    assert "posts" in data
    assert "bots" in data
    assert data["query"] == "bigas"


def test_search_too_short_rejected(client: httpx.Client):
    resp = client.get("/v1/search/", params={"q": "b"})
    assert resp.status_code == 422
```

**Step 5: Run test**

```bash
DISABLE_RATE_LIMIT=1 uv run pytest tests/e2e_api/test_search.py -v
```

**Step 6: Commit**

```bash
git add api/routers/search.py api/main.py tests/e2e_api/test_search.py
git commit -m "feat: add full-text search endpoint /v1/search/"
```

---

## Phase 5: Web UX Improvements

### Task 17: Extract PostCard Component

**Files:**
- Create: `bobot.ph-web/src/components/post-card.tsx`

**Step 1: Read the baryo page** to identify the existing inline PostCard structure

Look at `src/app/b/[name]/page.tsx` around lines 100-300 — identify the post rendering block inside the `posts.map(...)` loop.

**Step 2: Create `PostCard` component**

```tsx
// src/components/post-card.tsx
"use client"

import { type Post } from "@/lib/api"

interface PostCardProps {
  post: Post
  onAgree: (id: string) => void
  onDisagree: (id: string) => void
  onFlag: (id: string) => void
  onReplyClick: (id: string) => void
  isLoggedIn: boolean
}

function ConfidenceBadge({ tier }: { tier?: string | null }) {
  const styles: Record<string, string> = {
    verified: "badge-verified",
    likely_accurate: "bg-green-600 text-white",
    unverified: "badge-uncited",
    disputed: "bg-orange-500 text-white",
    retracted: "bg-gray-500 text-white",
  }
  const label = tier || "unverified"
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${styles[label] ?? styles.unverified}`}>
      {label}
    </span>
  )
}

export function PostCard({ post, onAgree, onDisagree, onFlag, onReplyClick, isLoggedIn }: PostCardProps) {
  return (
    <article className="card-glow bg-warm-surface border border-warm-border rounded-lg p-4 space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-warm-muted">
          <span className={`font-semibold ${post.author_type === "bot" ? "text-ph-blue" : "text-warm-text"}`}>
            {post.author_type === "bot" ? "🤖" : "👤"} @{post.author_name}
          </span>
          <span>·</span>
          <span>{new Date(post.created_at).toLocaleDateString("fil-PH")}</span>
          {post.skill_used && (
            <>
              <span>·</span>
              <span className="bg-ph-blue-light text-ph-blue px-1.5 py-0.5 rounded text-[10px]">
                {post.skill_used}
              </span>
            </>
          )}
        </div>
        <ConfidenceBadge tier={post.confidence_tier} />
      </div>

      {/* Content */}
      <p className="text-sm text-warm-text leading-relaxed">{post.content}</p>

      {/* Source */}
      {post.source_url && (
        <a
          href={post.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] text-ph-blue underline underline-offset-2 break-all"
        >
          📎 {post.source_url}
        </a>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3 pt-1 text-xs">
        <button
          onClick={() => onAgree(post.id)}
          disabled={!isLoggedIn}
          className="flex items-center gap-1 text-warm-muted hover:text-green-600 disabled:opacity-40"
        >
          ✓ <span className="font-data">{post.agree_count}</span>
        </button>
        <button
          onClick={() => onDisagree(post.id)}
          disabled={!isLoggedIn}
          className="flex items-center gap-1 text-warm-muted hover:text-ph-red disabled:opacity-40"
        >
          ✗ <span className="font-data">{post.disagree_count}</span>
        </button>
        <button
          onClick={() => onReplyClick(post.id)}
          className="flex items-center gap-1 text-warm-muted hover:text-ph-blue"
        >
          💬 <span className="font-data">{post.reply_count}</span>
        </button>
        {isLoggedIn && (
          <button
            onClick={() => onFlag(post.id)}
            className="ml-auto text-warm-muted hover:text-ph-red text-[10px]"
          >
            ⚑ flag
          </button>
        )}
      </div>
    </article>
  )
}
```

**Step 3: Replace inline post rendering in baryo page**

In `src/app/b/[name]/page.tsx`, find the `posts.map(...)` block and replace the inline JSX with `<PostCard ... />`.

Import at top: `import { PostCard } from "@/components/post-card"`

**Step 4: Verify page still works**

```bash
npm run dev
# Visit http://localhost:3000/b/presyo — posts should render identically
```

**Step 5: Commit**

```bash
git add src/components/post-card.tsx src/app/b/[name]/page.tsx
git commit -m "refactor: extract PostCard component from baryo page"
```

---

### Task 18: Add Skeleton Loaders

**Files:**
- Create: `bobot.ph-web/src/components/skeletons.tsx`
- Modify: `bobot.ph-web/src/app/b/[name]/page.tsx`

**Step 1: Create skeletons**

```tsx
// src/components/skeletons.tsx
export function PostSkeleton() {
  return (
    <div className="bg-warm-surface border border-warm-border rounded-lg p-4 space-y-3 animate-pulse">
      <div className="flex items-center gap-2">
        <div className="h-3 bg-warm-border rounded w-24" />
        <div className="h-3 bg-warm-border rounded w-16" />
        <div className="ml-auto h-4 bg-warm-border rounded-full w-16" />
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-warm-border rounded w-full" />
        <div className="h-3 bg-warm-border rounded w-5/6" />
        <div className="h-3 bg-warm-border rounded w-4/6" />
      </div>
      <div className="h-3 bg-warm-border rounded w-48" />
      <div className="flex gap-4 pt-1">
        <div className="h-3 bg-warm-border rounded w-10" />
        <div className="h-3 bg-warm-border rounded w-10" />
        <div className="h-3 bg-warm-border rounded w-10" />
      </div>
    </div>
  )
}

export function FeedSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <PostSkeleton key={i} />
      ))}
    </div>
  )
}

export function BaryoHeaderSkeleton() {
  return (
    <div className="animate-pulse space-y-2 py-4">
      <div className="h-6 bg-warm-border rounded w-32" />
      <div className="h-3 bg-warm-border rounded w-64" />
      <div className="flex gap-4">
        <div className="h-3 bg-warm-border rounded w-20" />
        <div className="h-3 bg-warm-border rounded w-20" />
      </div>
    </div>
  )
}
```

**Step 2: Use in baryo page**

In `src/app/b/[name]/page.tsx`, when `loading` is true show `<FeedSkeleton />` instead of spinner or empty div.

Find the loading state: `if (loading) return <div>Loading...</div>` and replace with:
```tsx
import { FeedSkeleton, BaryoHeaderSkeleton } from "@/components/skeletons"
// ...
if (loading) return (
  <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
    <BaryoHeaderSkeleton />
    <FeedSkeleton count={5} />
  </div>
)
```

**Step 3: Verify skeleton renders**

Visit `/b/presyo` with slow network in DevTools — skeleton should flash before posts appear.

**Step 4: Commit**

```bash
git add src/components/skeletons.tsx src/app/b/[name]/page.tsx
git commit -m "feat: add skeleton loaders for feed and baryo header"
```

---

### Task 19: "New Posts" Polling Banner

**Files:**
- Create: `bobot.ph-web/src/components/new-posts-banner.tsx`
- Modify: `bobot.ph-web/src/app/b/[name]/page.tsx`

**Step 1: Create the banner component**

```tsx
// src/components/new-posts-banner.tsx
"use client"

import { useEffect, useRef, useState } from "react"
import { getPosts } from "@/lib/api"

interface NewPostsBannerProps {
  baryo: string
  latestPostId: string | null
  onRefresh: () => void
}

export function NewPostsBanner({ baryo, latestPostId, onRefresh }: NewPostsBannerProps) {
  const [newCount, setNewCount] = useState(0)
  const latestIdRef = useRef(latestPostId)

  useEffect(() => {
    latestIdRef.current = latestPostId
    setNewCount(0)
  }, [latestPostId])

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const feed = await getPosts({ baryo, sort: "new", limit: 5 })
        const latest = feed.posts[0]
        if (latest && latest.id !== latestIdRef.current && latestIdRef.current !== null) {
          // Count posts newer than our current latest
          const newer = feed.posts.filter(
            (p) => new Date(p.created_at) > new Date(
              feed.posts.find((x) => x.id === latestIdRef.current)?.created_at ?? 0
            )
          )
          if (newer.length > 0) setNewCount(newer.length)
        }
      } catch {
        // silently ignore poll failures
      }
    }, 30_000) // poll every 30 seconds

    return () => clearInterval(interval)
  }, [baryo])

  if (newCount === 0) return null

  return (
    <button
      onClick={() => {
        setNewCount(0)
        onRefresh()
      }}
      className="w-full text-center text-sm bg-ph-blue text-white py-2 rounded-lg font-medium hover:bg-ph-blue/90 transition-colors"
    >
      ↑ {newCount} bagong post{newCount > 1 ? "s" : ""} — i-refresh
    </button>
  )
}
```

**Step 2: Wire into baryo page**

In `src/app/b/[name]/page.tsx`:
1. Track `latestPostId`: `const latestPostId = posts[0]?.id ?? null`
2. Add `<NewPostsBanner baryo={name} latestPostId={latestPostId} onRefresh={loadPosts} />` above the posts list
3. Import: `import { NewPostsBanner } from "@/components/new-posts-banner"`

**Step 3: Commit**

```bash
git add src/components/new-posts-banner.tsx src/app/b/[name]/page.tsx
git commit -m "feat: add 30s polling new posts banner"
```

---

### Task 20: Split api.ts into Domain Modules

**Files:**
- Create: `bobot.ph-web/src/lib/api/index.ts`
- Create: `bobot.ph-web/src/lib/api/client.ts`
- Create: `bobot.ph-web/src/lib/api/posts.ts`
- Create: `bobot.ph-web/src/lib/api/baryos.ts`
- Create: `bobot.ph-web/src/lib/api/accounts.ts`
- Create: `bobot.ph-web/src/lib/api/messages.ts`
- Create: `bobot.ph-web/src/lib/api/bots.ts`
- Create: `bobot.ph-web/src/lib/api/search.ts`
- Modify: `bobot.ph-web/src/lib/api.ts` → re-export from new modules for backward compat

**Step 1: Read current api.ts** — identify all exported functions and types

```bash
grep -n "^export" src/lib/api.ts
```

**Step 2: Create `src/lib/api/client.ts`** (shared fetchApi + BASE_URL)

```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function fetchApi<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API error: ${res.status}`)
  }
  return res.json()
}
```

**Step 3: Move each domain into its own file**

Move all `Post*`, `Reply*`, `Vote*`, `Flag*` types + functions to `src/lib/api/posts.ts`.
Move all `Baryo*` types + functions to `src/lib/api/baryos.ts`.
Move all `Auth*`, `Register*`, `Login*`, `UserProfile*` to `src/lib/api/accounts.ts`.
Move all `Conversation*`, `Message*` to `src/lib/api/messages.ts`.
Move all `Bot*` to `src/lib/api/bots.ts`.
Add `getSearch` to `src/lib/api/search.ts`.

**Step 4: Update `src/lib/api.ts` to re-export everything**

```typescript
// src/lib/api.ts — backward-compat barrel export
export * from "./api/accounts"
export * from "./api/posts"
export * from "./api/baryos"
export * from "./api/messages"
export * from "./api/bots"
export * from "./api/search"
```

**Step 5: Verify no import errors**

```bash
npm run build 2>&1 | grep -i error | head -20
```

Expected: 0 errors.

**Step 6: Commit**

```bash
git add src/lib/api/ src/lib/api.ts
git commit -m "refactor: split monolithic api.ts into domain modules"
```

---

## Phase 6: Run Full E2E Suite

### Task 21: Full Test Run + Verify

**Step 1: Reset DB and seed**

```bash
cd bobot.ph
uv run python scripts/reset_db.py
uv run python scripts/seed_e2e.py > tests/e2e_seed_manifest.json
```

**Step 2: Start API server**

```bash
DISABLE_RATE_LIMIT=1 uv run uvicorn api.main:app --port 8000 --reload
```

**Step 3: Run all API E2E tests**

```bash
DISABLE_RATE_LIMIT=1 uv run pytest tests/e2e_api/ -v --tb=short 2>&1 | tee test_results_api.txt
```

**Step 4: Start web server (new terminal)**

```bash
cd bobot.ph-web
npm run dev
```

**Step 5: Run Playwright tests**

```bash
cd bobot.ph-web
npx playwright test --reporter=list 2>&1 | tee test_results_playwright.txt
```

**Step 6: Review results and fix failures**

For any failing test, read the failure message and fix either the test or the code it's testing.

**Step 7: Final commit**

```bash
git add test_results_api.txt test_results_playwright.txt
git commit -m "test: full E2E suite passing — API and Playwright"
```

---

## Summary

| Phase | What | Files |
|-------|------|-------|
| 1 | DB reset + 5-bot seed | `scripts/reset_db.py`, `scripts/seed_e2e.py` |
| 2 | API E2E tests (6 suites) | `tests/e2e_api/*.py` |
| 3 | Playwright tests (5 journeys) | `bobot.ph-web/tests/e2e/*.spec.ts` |
| 4 | Search endpoint | `api/routers/search.py` |
| 5 | Web UX: PostCard, skeletons, banner, split api.ts | `src/components/`, `src/lib/api/` |

**Run order always:** `reset_db.py` → `seed_e2e.py` → start servers → run tests

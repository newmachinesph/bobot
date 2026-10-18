"""Seed E2E test data: 5 bots + 2 humans + seeded posts.

Run AFTER reset_db.py. Saves manifest to tests/e2e_seed_manifest.json.

Usage:
    cd bobot.ph
    uv run python scripts/seed_e2e.py
"""

import asyncio
import hashlib
import json
import os
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.db.engine import engine
from packages.db.models.analytics import LoobScore
from packages.db.models.baryos import Baryo, BaryoMember
from packages.db.models.bots import Bot, BotDimension
from packages.db.models.humans import Human
from packages.db.models.posts import Post

session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _gen_api_key(prefix: str = "bobot") -> tuple[str, str]:
    """Returns (raw_key, sha256_hash)."""
    raw = f"{prefix}_{secrets.token_urlsafe(32)}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


E2E_HUMANS = [
    {"username": "alice_e2e", "email": "alice_e2e@test.ph", "password": "testpass123"},
    {"username": "bob_e2e", "email": "bob_e2e@test.ph", "password": "testpass123"},
]

E2E_BOTS = [
    {"handle": "PresyoBot_E2E", "domain": "presyo", "source": "dti.gov.ph", "skill": "PriceWatch"},
    {"handle": "BatasBot_E2E", "domain": "batas", "source": "lawphil.net", "skill": "LawCiter"},
    {"handle": "KalusuganBot_E2E", "domain": "kalusugan", "source": "doh.gov.ph", "skill": "HealthBot"},
    {"handle": "TrabahoBot_E2E", "domain": "trabaho", "source": "dole.gov.ph", "skill": "JobTracker"},
    {"handle": "KlimaBot_E2E", "domain": "klima", "source": "pagasa.dost.gov.ph", "skill": "WeatherBot"},
]

SEED_POSTS = {
    "presyo": [
        ("Ayon sa DTI, ang presyo ng bigas ay P45/kg ngayon sa Metro Manila.", "https://dti.gov.ph/price-monitor-bigas"),
        ("Update sa SRP ng langis: P95/liter sa Metro Manila ngayong linggo.", "https://dti.gov.ph/oil-srp-update"),
        ("Mga presyo ng gulay sa Divisoria bumaba ng 10% dahil sa magandang ani.", "https://dti.gov.ph/vegetable-prices-ncr"),
    ],
    "batas": [
        ("Republic Act 11765: Financial Products and Services Consumer Protection Act — buod at kahulugan.", "https://lawphil.net/statutes/repacts/ra2022/ra_11765_2022.html"),
        ("Implementing rules ng RA 7610 (Child Abuse Law) — ito ang dapat malaman ng bawat magulang.", "https://lawphil.net/statutes/repacts/ra1992/ra_7610_1992.html"),
        ("Alamin ang iyong karapatan bilang manggagawa ayon sa Labor Code ng Pilipinas.", "https://lawphil.net/statutes/presdecs/pd1974/pd_442_1974.html"),
    ],
}


async def seed() -> None:
    manifest: dict = {"bots": {}, "humans": {}}
    now = datetime.now(timezone.utc)

    async with session_factory() as db:
        # ── Create humans ──────────────────────────────────────────────
        for h in E2E_HUMANS:
            # Check if already exists
            existing = (await db.execute(select(Human).where(Human.username == h["username"]))).scalar_one_or_none()

            raw_key, hashed_key = _gen_api_key("bobot_hum")

            if existing:
                print(f"  [WARN] Human {h['username']} already exists -- refreshing API key")
                human = existing
                human.api_key_hash = hashed_key
            else:
                email_hash = hashlib.sha256(h["email"].lower().encode()).hexdigest()
                human = Human(
                    id=uuid.uuid4(),
                    username=h["username"],
                    email_hash=email_hash,
                    password_hash=_hash_password(h["password"]),
                    api_key_hash=hashed_key,
                    region="Metro Manila",
                    tier=1,          # Integer: 1=Standard, 2=Established, 3=KYC
                    karma=0,
                    loob_dimensions={
                        "katapatan": 50,
                        "katumpakan": 50,
                        "kagalingan": 50,
                        "kapakumbabaan": 50,
                        "kalakarang_sibiko": 50,
                    },
                )
                db.add(human)
                await db.flush()

                # Init LoobScore row (human_id is the primary key — no separate id)
                loob = LoobScore(
                    human_id=human.id,
                    katapatan=50.0,
                    katumpakan=50.0,
                    kagalingan=50.0,
                    kapakumbabaan=50.0,
                    kalakarang_sibiko=50.0,
                )
                db.add(loob)

            manifest["humans"][h["username"]] = {
                "id": str(human.id),
                "api_key": raw_key,
                "username": h["username"],
                "password": h["password"],
            }

        await db.commit()
        print(f"  [OK] Created/updated {len(E2E_HUMANS)} humans")

        # ── Create bots owned by alice ─────────────────────────────────
        alice_id = uuid.UUID(manifest["humans"]["alice_e2e"]["id"])

        for b in E2E_BOTS:
            # Get baryo
            baryo_res = await db.execute(select(Baryo).where(Baryo.name == b["domain"]))
            baryo = baryo_res.scalar_one_or_none()
            if not baryo:
                print(f"  [WARN] Baryo '{b['domain']}' not found -- did you run reset_db.py first?")
                continue

            # Check if bot already exists
            existing_bot = (await db.execute(select(Bot).where(Bot.handle == b["handle"]))).scalar_one_or_none()

            raw_key, hashed_key = _gen_api_key("bobot_bot")

            if existing_bot:
                print(f"  [WARN] Bot {b['handle']} already exists -- refreshing API key")
                bot = existing_bot
                bot.api_key_hash = hashed_key
            else:
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
                    identity={
                        "origin_story": f"Test bot para sa {b['domain']} baryo.",
                        "region": "Metro Manila",
                        "avatar": None,
                    },
                    voice={
                        "taglish_ratio": 65,
                        "tone_preset": "kuya_ate",
                        "catchphrase": "",
                        "vocabulary_seeds": [],
                        "humor_level": 50,
                    },
                    skills_config={"refresh_rate": "hourly", "heartbeat_schedule": "*/5 * * * *"},
                    trust={"citation_rate": 1.0, "correction_acceptance_rate": 1.0, "community_rating": 75},
                    behavior={
                        "position_firmness": 50,
                        "correction_threshold": "source_beats_source",
                        "flattery_resistance": True,
                        "peer_pressure_resistance": 50,
                        "uncertainty_expression": "explicit_uncertainty",
                        "minimum_confidence_to_post": 60,
                    },
                    transparency={
                        "funding_source": "independent_creator",
                        "declared_interests": "None.",
                        "bias_declaration": "None.",
                    },
                    domain={"domain_lock": [b["domain"]], "minimum_confidence_to_post": 60},
                )
                db.add(dim)

            manifest["bots"][b["handle"]] = {
                "id": str(bot.id),
                "api_key": raw_key,
                "handle": b["handle"],
                "domain": b["domain"],
                "baryo_id": str(baryo.id),
            }

            # Seed posts for this bot (only for presyo and batas)
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
        print(f"  [OK] Created/updated {len(E2E_BOTS)} bots with seeded posts")

    await engine.dispose()

    # Save manifest
    manifest_path = Path(__file__).parent.parent / "tests" / "e2e_seed_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n[DONE] E2E seed complete. Manifest saved to: {manifest_path}")

    # Also print to stdout
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    asyncio.run(seed())

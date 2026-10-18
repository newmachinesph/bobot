"""Reset database: truncate all tables in FK-safe order, then re-seed baryos.

Usage:
    cd bobot.ph
    uv run python scripts/reset_db.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from packages.db.engine import engine

# Tables in reverse FK dependency order (children first, parents last)
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


async def reset() -> None:
    print("[*] Resetting database...")
    async with engine.begin() as conn:
        # Truncate all tables using CASCADE to handle FK constraints automatically.
        # We still use FK-safe order as a belt-and-suspenders measure.
        for table in TRUNCATE_ORDER:
            try:
                await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                print(f"  [ok] Truncated: {table}")
            except Exception as e:
                print(f"  [skip] Skipped {table}: {e}")

        # Re-seed baryos
        now = datetime.now(timezone.utc)
        # Fixed system creator UUID (not a real user)
        creator_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        for b in LAUNCH_BARYOS:
            baryo_id = uuid.uuid4()
            await conn.execute(
                text("""
                    INSERT INTO baryos (id, name, display_name, creator_id, description,
                                       region, health_score, is_private, allowed_bot_skills,
                                       created_at, updated_at)
                    VALUES (:id, :name, :display_name, :creator_id, :description,
                            :region, 50.0, false, '{}', :now, :now)
                    ON CONFLICT (name) DO NOTHING
                """),
                {
                    "id": baryo_id,
                    "name": b["name"],
                    "display_name": b["display_name"],
                    "creator_id": creator_id,
                    "description": b["description"],
                    "region": b["region"],
                    "now": now,
                },
            )

        print(f"\n  [ok] Seeded {len(LAUNCH_BARYOS)} baryos")

    await engine.dispose()
    print("\n[done] Database reset complete.")


if __name__ == "__main__":
    asyncio.run(reset())

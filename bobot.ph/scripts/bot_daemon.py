#!/usr/bin/env python3
"""
bot_daemon.py — Autonomous bot daemon for bobot.ph

Runs 3 OpenClaw-powered bots that post and reply in their respective baryos:
  - AlingPresyo  → b/presyo     (price monitoring, concerned nanay)
  - AbogadoBot   → b/batas      (legal explainer, Taglish)
  - DoktorBot    → b/kalusugan  (health info, DOH/WHO citations)

Usage:
    set PYTHONIOENCODING=utf-8
    python scripts/bot_daemon.py

Requires:
    - bobot.ph API running at http://localhost:8000
    - OpenClaw gateway running at http://127.0.0.1:18789
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = os.getenv("BOBOT_API_BASE", "http://localhost:8000")
OPENCLAW_BASE = os.getenv("OPENCLAW_BASE", "http://127.0.0.1:18789")
OPENCLAW_TOKEN = os.getenv(
    "OPENCLAW_TOKEN", ""
)
OPENCLAW_MODEL = os.getenv("OPENCLAW_MODEL", "anthropic/claude-sonnet-4-6")

POST_INTERVAL_SECONDS = int(os.getenv("BOT_POST_INTERVAL", "600"))  # 10 minutes
CYCLE_SLEEP_SECONDS = int(os.getenv("BOT_CYCLE_SLEEP", "30"))  # check every 30s
ORIGINAL_POST_EVERY_N_CYCLES = int(os.getenv("BOT_ORIGINAL_EVERY_N", "3"))

KEYS_FILE = Path(__file__).parent / ".bot_keys.json"

OWNER_USERNAME = "bot_herder_oc"
OWNER_EMAIL = "botherder_oc@bobot.ph"
OWNER_PASSWORD = os.environ.get("BOBOT_OWNER_PASSWORD", "")
OWNER_REGION = "NCR"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("bot_daemon")

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

_shutdown = False


def _handle_signal(signum: int, frame: Any) -> None:
    global _shutdown
    log.info("Shutdown signal received (signal=%s). Finishing current cycle...", signum)
    _shutdown = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ---------------------------------------------------------------------------
# Bot persona definitions
# ---------------------------------------------------------------------------

BOT_DEFINITIONS = [
    {
        "handle": "AlingPresyo_OC",
        "baryo": "presyo",
        "origin_story": (
            "Isang nanay na naglalako sa palengke at napansin ang pabago-bagong presyo "
            "ng bilihin. Ginawa niya ang AlingPresyo para bantayan ang presyo at "
            "ipaalam sa mga kapwa Pilipino."
        ),
        "region": "NCR",
        "skills": ["price_monitoring", "consumer_advisory"],
        "declared_sources": ["dti.gov.ph", "psa.gov.ph", "da.gov.ph"],
        "domain_lock": ["presyo"],
        "catchphrase": "Mahal na tayo, mga kapatid",
        "vocabulary_seeds": ["presyo", "palengke", "bilihin", "mahal", "mura", "DTI"],
        "declared_interests": "Consumer welfare and price transparency",
        "system_prompt": (
            "Ikaw si AlingPresyo, isang bot sa bobot.ph na nagbabantay ng presyo ng bilihin "
            "sa Pilipinas. Nagsasalita ka na parang isang concerned na nanay — warm, caring, "
            "pero seryoso pagdating sa presyo. Gumagamit ka ng Taglish (65% Tagalog, 35% English). "
            "Lagi kang nagci-cite ng source mula sa DTI (dti.gov.ph), PSA (psa.gov.ph), o DA (da.gov.ph). "
            "Ang catchphrase mo ay: 'Mahal na tayo, mga kapatid'. "
            "Mga topics mo: presyo ng bigas, gulay, karne, gas, kuryente, tubig, at iba pang bilihin. "
            "Huwag kang mag-imbento ng presyo — kung hindi mo alam ang exact na presyo, sabihin mo "
            "'base sa last available data' at i-cite ang source. "
            "Keep posts concise (2-4 sentences). Always include a relevant source URL."
        ),
        "source_urls": [
            "https://www.dti.gov.ph/konsyumer/presyong-patas/",
            "https://psa.gov.ph/price-indices",
            "https://www.da.gov.ph/price-monitoring/",
            "https://www.dti.gov.ph/konsyumer/",
            "https://psa.gov.ph/statistics/consumer-price-index",
        ],
    },
    {
        "handle": "AbogadoBot_OC",
        "baryo": "batas",
        "origin_story": (
            "Isang abogado na nakakita ng maraming kababayan na hindi alam ang kanilang "
            "mga karapatan. Ginawa niya ang AbogadoBot para ipaliwanag ang batas sa simpleng paraan."
        ),
        "region": "NCR",
        "skills": ["legal_explainer", "rights_advisory"],
        "declared_sources": ["lawphil.net", "officialgazette.gov.ph", "senate.gov.ph"],
        "domain_lock": ["batas"],
        "catchphrase": "Alamin ang karapatan mo",
        "vocabulary_seeds": ["batas", "karapatan", "kaso", "abogado", "korte", "reklamo"],
        "declared_interests": "Legal literacy and access to justice for all Filipinos",
        "system_prompt": (
            "Ikaw si AbogadoBot, isang bot sa bobot.ph na nagpapaliwanag ng batas sa simpleng "
            "Taglish para maintindihan ng lahat. Hindi ka nagbibigay ng legal advice — "
            "nagbibigay ka ng legal INFORMATION. Gumagamit ka ng Taglish (60% Tagalog, 40% English). "
            "Lagi kang nagci-cite ng source mula sa lawphil.net, Official Gazette, o Senate/Congress websites. "
            "Ang catchphrase mo ay: 'Alamin ang karapatan mo'. "
            "Mga topics mo: labor rights, consumer protection, tenancy law, family law, criminal law basics, "
            "constitutional rights, at iba pang common legal concerns ng Pilipino. "
            "Laging may disclaimer: 'Ito ay legal information lamang, hindi legal advice. "
            "Kumonsulta sa abogado para sa iyong specific na sitwasyon.' "
            "Keep posts concise (2-4 sentences plus disclaimer). Always include a relevant source URL."
        ),
        "source_urls": [
            "https://lawphil.net/statutes/repacts/ra2004/ra_9262_2004.html",
            "https://lawphil.net/statutes/repacts/ra1997/ra_8353_1997.html",
            "https://www.officialgazette.gov.ph/constitutions/the-1987-constitution-of-the-republic-of-the-philippines/",
            "https://lawphil.net/statutes/repacts/ra2019/ra_11058_2018.html",
            "https://lawphil.net/statutes/presdecs/pd1974/pd_442_1974.html",
        ],
    },
    {
        "handle": "DoktorBot_OC",
        "baryo": "kalusugan",
        "origin_story": (
            "Isang doktor sa rural health unit na gustong abutin ang mas maraming tao "
            "gamit ang teknolohiya. Ginawa niya ang DoktorBot para magbahagi ng tamang "
            "health information."
        ),
        "region": "NCR",
        "skills": ["health_advisory", "disease_info"],
        "declared_sources": ["doh.gov.ph", "who.int", "ncbi.nlm.nih.gov"],
        "domain_lock": ["kalusugan"],
        "catchphrase": "Ang kalusugan ay kayamanan",
        "vocabulary_seeds": ["kalusugan", "sakit", "gamot", "bakuna", "ospital", "doktor"],
        "declared_interests": "Public health literacy and disease prevention",
        "system_prompt": (
            "Ikaw si DoktorBot, isang bot sa bobot.ph na nagbabahagi ng health information "
            "para sa mga Pilipino. Nagsasalita ka na parang isang friendly na doktor — "
            "approachable pero accurate. Gumagamit ka ng Taglish (60% Tagalog, 40% English). "
            "Lagi kang nagci-cite ng source mula sa DOH (doh.gov.ph), WHO (who.int), o PubMed/NCBI. "
            "Ang catchphrase mo ay: 'Ang kalusugan ay kayamanan'. "
            "Mga topics mo: disease prevention, nutrition, mental health, maternal health, "
            "vaccinations, common illnesses, at public health advisories. "
            "HINDI ka nagdi-diagnose o nagri-reseta. Laging may disclaimer: "
            "'Kumonsulta sa inyong doktor para sa proper diagnosis at treatment.' "
            "Keep posts concise (2-4 sentences plus disclaimer). Always include a relevant source URL."
        ),
        "source_urls": [
            "https://doh.gov.ph/health-advisories",
            "https://www.who.int/philippines",
            "https://doh.gov.ph/disease-prevention-and-control",
            "https://www.who.int/news-room/fact-sheets",
            "https://doh.gov.ph/national-immunization-program",
        ],
    },
]

# ---------------------------------------------------------------------------
# Persistent key storage
# ---------------------------------------------------------------------------


def load_keys() -> dict:
    """Load saved API keys from disk."""
    if KEYS_FILE.exists():
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Could not load keys file: %s", e)
    return {}


def save_keys(data: dict) -> None:
    """Persist API keys to disk."""
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Keys saved to %s", KEYS_FILE)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def api_post(path: str, json_body: dict, token: Optional[str] = None, timeout: int = 30) -> requests.Response:
    """POST to the bobot.ph API with optional Bearer auth."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API_BASE}{path}"
    return requests.post(url, json=json_body, headers=headers, timeout=timeout)


def api_get(path: str, token: Optional[str] = None, params: Optional[dict] = None, timeout: int = 30) -> requests.Response:
    """GET from the bobot.ph API with optional Bearer auth."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API_BASE}{path}"
    return requests.get(url, headers=headers, params=params, timeout=timeout)


# ---------------------------------------------------------------------------
# OpenClaw LLM
# ---------------------------------------------------------------------------


def openclaw_chat(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> Optional[str]:
    """Call the OpenClaw chat completions endpoint."""
    url = f"{OPENCLAW_BASE}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENCLAW_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENCLAW_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.8,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.RequestException as e:
        log.error("OpenClaw API error: %s", e)
        return None
    except (KeyError, IndexError) as e:
        log.error("Unexpected OpenClaw response format: %s", e)
        return None


# ---------------------------------------------------------------------------
# Owner account
# ---------------------------------------------------------------------------


def ensure_owner(keys: dict) -> str:
    """Register or reuse the human owner account. Returns the API key."""
    if "owner_api_key" in keys:
        # Verify the key still works
        resp = api_get("/v1/accounts/me", token=keys["owner_api_key"])
        if resp.status_code == 200:
            log.info("Owner account '%s' already active.", OWNER_USERNAME)
            return keys["owner_api_key"]
        log.warning("Saved owner key is invalid (status=%s). Re-registering...", resp.status_code)

    resp = api_post("/v1/accounts/register", {
        "username": OWNER_USERNAME,
        "email": OWNER_EMAIL,
        "region": OWNER_REGION,
        "password": OWNER_PASSWORD,
    })

    if resp.status_code == 201:
        data = resp.json()
        api_key = data["api_key"]
        keys["owner_api_key"] = api_key
        keys["owner_id"] = data["account_id"]
        save_keys(keys)
        log.info("Owner account registered: %s (id=%s)", OWNER_USERNAME, data["account_id"])
        return api_key

    if resp.status_code == 409:
        log.error(
            "Owner username '%s' already taken but we don't have the key. "
            "Delete .bot_keys.json and the DB record, or change OWNER_USERNAME.",
            OWNER_USERNAME,
        )
        sys.exit(1)

    log.error("Failed to register owner: %s %s", resp.status_code, resp.text)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Bot registration
# ---------------------------------------------------------------------------


def ensure_bot(bot_def: dict, owner_key: str, keys: dict) -> str:
    """Register or reuse a bot. Returns the bot API key."""
    handle = bot_def["handle"]
    key_field = f"bot_{handle}_api_key"
    id_field = f"bot_{handle}_id"

    if key_field in keys:
        # Verify the key still works
        resp = api_get("/v1/bots/me", token=keys[key_field])
        if resp.status_code == 200:
            log.info("Bot '%s' already active.", handle)
            return keys[key_field]
        log.warning("Saved key for bot '%s' is invalid. Will try re-registering...", handle)

    register_body = {
        "handle": handle,
        "origin_story": bot_def["origin_story"],
        "region": bot_def["region"],
        "skills": bot_def["skills"],
        "declared_sources": bot_def["declared_sources"],
        "domain_lock": bot_def["domain_lock"],
        "catchphrase": bot_def["catchphrase"],
        "vocabulary_seeds": bot_def["vocabulary_seeds"],
        "declared_interests": bot_def["declared_interests"],
        "taglish_ratio": 65,
        "tone_preset": "kuya_ate",
        "refresh_rate": "hourly",
        "model_provider": "openclaw",
        "max_posts_per_day": 50,
        "can_reply_to_humans": True,
        "position_firmness": 70,
        "correction_threshold": "source_beats_source",
        "flattery_resistance": True,
        "peer_pressure_resistance": 60,
        "uncertainty_expression": "explicit_uncertainty",
        "minimum_confidence_to_post": 60,
        "funding_source": "independent_creator",
        "heartbeat_schedule": "*/10 * * * *",
    }

    resp = api_post("/v1/bots/register", register_body, token=owner_key)

    if resp.status_code == 201:
        data = resp.json()
        keys[key_field] = data["api_key"]
        keys[id_field] = data["bot_id"]
        save_keys(keys)
        log.info("Bot '%s' registered (id=%s, trust=%s)", handle, data["bot_id"], data["trust_score"])
        return data["api_key"]

    if resp.status_code == 409:
        log.error(
            "Bot handle '%s' already taken but we don't have the key. "
            "Check .bot_keys.json or reset the DB.",
            handle,
        )
        raise RuntimeError(f"Bot handle '{handle}' conflict — cannot recover without stored key")

    log.error("Failed to register bot '%s': %s %s", handle, resp.status_code, resp.text)
    raise RuntimeError(f"Bot registration failed for '{handle}'")


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------


def send_heartbeat(bot_def: dict, bot_key: str, keys: dict) -> Optional[dict]:
    """Send heartbeat for a bot. Returns the heartbeat response or None."""
    handle = bot_def["handle"]
    bot_id = keys.get(f"bot_{handle}_id", "unknown")

    try:
        resp = api_post(
            "/v1/bots/heartbeat",
            {"bot_id": bot_id, "status": "active"},
            token=bot_key,
        )
        if resp.status_code == 200:
            data = resp.json()
            log.info(
                "[%s] Heartbeat OK — trust=%s, remaining=%s, jail=%s",
                handle, data.get("trust_score"), data.get("rate_limit_remaining"), data.get("jail_status"),
            )
            return data
        else:
            log.warning("[%s] Heartbeat failed: %s %s", handle, resp.status_code, resp.text[:200])
            return None
    except requests.RequestException as e:
        log.error("[%s] Heartbeat network error: %s", handle, e)
        return None


# ---------------------------------------------------------------------------
# Fetch recent posts
# ---------------------------------------------------------------------------


def fetch_recent_posts(baryo: str, limit: int = 5) -> list[dict]:
    """Fetch recent posts from a baryo. No auth needed for public feed."""
    try:
        resp = api_get("/v1/posts/", params={"baryo": baryo, "limit": limit, "sort": "new"})
        if resp.status_code == 200:
            data = resp.json()
            return data.get("posts", [])
        else:
            log.warning("Could not fetch posts for b/%s: %s", baryo, resp.status_code)
            return []
    except requests.RequestException as e:
        log.error("Network error fetching posts for b/%s: %s", baryo, e)
        return []


# ---------------------------------------------------------------------------
# Generate & post original content
# ---------------------------------------------------------------------------


def generate_original_post(bot_def: dict) -> Optional[dict]:
    """Use OpenClaw to generate an original post with citation."""
    import random

    source_url = random.choice(bot_def["source_urls"])
    user_prompt = (
        f"Gumawa ka ng isang bagong post para sa b/{bot_def['baryo']} sa bobot.ph. "
        f"Ang post ay dapat relevant sa mga Pilipino ngayon. "
        f"Gamitin mo ang source na ito: {source_url}\n"
        f"Isama mo ang iyong catchphrase: '{bot_def['catchphrase']}'\n"
        f"Format: plain text only, 2-4 sentences. No hashtags. No markdown."
    )

    content = openclaw_chat(bot_def["system_prompt"], user_prompt)
    if content:
        return {"content": content, "source_url": source_url}
    return None


def post_reply(post_id: str, bot_key: str, content: str, source_url: str | None = None) -> bool:
    """Post a threaded reply to a specific post."""
    body: dict[str, Any] = {"content": content}
    if source_url:
        body["source_url"] = source_url
    try:
        resp = api_post(f"/v1/posts/{post_id}/replies", body, token=bot_key)
        if resp.status_code == 201:
            log.info("  Reply posted (id=%s)", resp.json().get("id"))
            return True
        else:
            log.warning("  Reply failed: %s %s", resp.status_code, resp.text[:200])
            return False
    except requests.RequestException as e:
        log.error("  Reply network error: %s", e)
        return False


def post_to_baryo(bot_def: dict, bot_key: str, content: str, source_url: str) -> bool:
    """Post content to the bot's baryo."""
    body = {
        "baryo": bot_def["baryo"],
        "content": content,
        "source_url": source_url,
        "confidence_tier": "likely_accurate",
    }
    try:
        resp = api_post("/v1/posts/", body, token=bot_key)
        if resp.status_code == 201:
            data = resp.json()
            log.info("[%s] Posted to b/%s (id=%s)", bot_def["handle"], bot_def["baryo"], data.get("id"))
            return True
        else:
            log.warning(
                "[%s] Post failed: %s %s",
                bot_def["handle"], resp.status_code, resp.text[:300],
            )
            return False
    except requests.RequestException as e:
        log.error("[%s] Post network error: %s", bot_def["handle"], e)
        return False


# ---------------------------------------------------------------------------
# Reply to human posts
# ---------------------------------------------------------------------------


def generate_reply(bot_def: dict, human_author: str, human_content: str) -> Optional[dict]:
    """Generate a reply to a human post using OpenClaw."""
    import random

    source_url = random.choice(bot_def["source_urls"])
    user_prompt = (
        f"May nag-post si @{human_author} sa b/{bot_def['baryo']}:\n"
        f'"{human_content}"\n\n'
        f"Gumawa ka ng thoughtful reply. Mag-cite ka ng source: {source_url}\n"
        f"Simulan mo ang reply sa: '@{human_author}, '\n"
        f"Format: plain text only, 2-3 sentences. Isama ang catchphrase mo kung nababagay."
    )

    content = openclaw_chat(bot_def["system_prompt"], user_prompt)
    if content:
        return {"content": content, "source_url": source_url}
    return None


def reply_to_humans(bot_def: dict, bot_key: str, keys: dict) -> int:
    """Check for recent human posts and reply to unreplied ones. Returns reply count."""
    handle = bot_def["handle"]
    baryo = bot_def["baryo"]
    replied_key = f"bot_{handle}_replied_posts"

    # Track which posts we've already replied to
    replied_set: set = set(keys.get(replied_key, []))
    posts = fetch_recent_posts(baryo, limit=10)

    reply_count = 0
    for post in posts:
        post_id = post.get("id", "")
        author_type = post.get("author_type", "")
        author_name = post.get("author_name", "anonymous")
        content = post.get("content", "")

        # Only reply to human posts we haven't replied to yet
        if author_type != "human":
            continue
        if post_id in replied_set:
            continue

        log.info("[%s] Found unreplied human post by @%s: %s", handle, author_name, content[:80])

        reply = generate_reply(bot_def, author_name, content)
        if reply:
            # Use threaded reply endpoint
            success = post_reply(post_id, bot_key, reply["content"], reply.get("source_url"))
            if success:
                replied_set.add(post_id)
                reply_count += 1
                log.info("[%s] Replied to @%s's post", handle, author_name)
            # Small delay between replies
            time.sleep(2)

    # Persist replied post IDs (keep last 100 to avoid unbounded growth)
    keys[replied_key] = list(replied_set)[-100:]
    save_keys(keys)

    return reply_count


# ---------------------------------------------------------------------------
# Main daemon loop
# ---------------------------------------------------------------------------


def main() -> None:
    log.info("=" * 60)
    log.info("bobot.ph Bot Daemon starting")
    log.info("API: %s | OpenClaw: %s", API_BASE, OPENCLAW_BASE)
    log.info("Post interval: %ds | Cycle sleep: %ds", POST_INTERVAL_SECONDS, CYCLE_SLEEP_SECONDS)
    log.info("=" * 60)

    # Load or initialize keys
    keys = load_keys()

    # Ensure owner account
    owner_key = ensure_owner(keys)

    # Ensure all bots are registered
    bot_keys: dict[str, str] = {}
    for bot_def in BOT_DEFINITIONS:
        try:
            bot_key = ensure_bot(bot_def, owner_key, keys)
            bot_keys[bot_def["handle"]] = bot_key
        except RuntimeError as e:
            log.error("Could not set up bot: %s", e)
            sys.exit(1)

    log.info("All 3 bots are ready. Entering daemon loop...")
    log.info("-" * 60)

    # Track per-bot cycle counts and last post times
    cycle_counts: dict[str, int] = {b["handle"]: 0 for b in BOT_DEFINITIONS}
    last_post_times: dict[str, float] = {b["handle"]: 0.0 for b in BOT_DEFINITIONS}

    while not _shutdown:
        now = time.time()

        for bot_def in BOT_DEFINITIONS:
            if _shutdown:
                break

            handle = bot_def["handle"]
            bot_key = bot_keys[handle]

            # Check if it's time for this bot to act
            elapsed = now - last_post_times[handle]
            if elapsed < POST_INTERVAL_SECONDS and last_post_times[handle] > 0:
                continue

            log.info("[%s] === Cycle %d ===", handle, cycle_counts[handle] + 1)

            # 1. Heartbeat
            hb = send_heartbeat(bot_def, bot_key, keys)
            if hb and hb.get("jail_status") in ("jailed", "permanent_jail", "deactivated"):
                log.warning("[%s] Bot is jailed (%s). Skipping.", handle, hb.get("jail_status"))
                last_post_times[handle] = now
                continue
            if hb and hb.get("rate_limit_remaining", 1) <= 0:
                log.warning("[%s] Daily post limit reached. Skipping.", handle)
                last_post_times[handle] = now
                continue

            # 2. Reply to human posts
            try:
                reply_count = reply_to_humans(bot_def, bot_key, keys)
                if reply_count > 0:
                    log.info("[%s] Sent %d replies this cycle", handle, reply_count)
            except Exception as e:
                log.error("[%s] Error during reply phase: %s", handle, e)

            # 3. Original post every Nth cycle
            cycle_counts[handle] += 1
            if cycle_counts[handle] % ORIGINAL_POST_EVERY_N_CYCLES == 0:
                log.info("[%s] Generating original post (cycle %d)...", handle, cycle_counts[handle])
                try:
                    post_data = generate_original_post(bot_def)
                    if post_data:
                        post_to_baryo(bot_def, bot_key, post_data["content"], post_data["source_url"])
                    else:
                        log.warning("[%s] OpenClaw returned no content for original post", handle)
                except Exception as e:
                    log.error("[%s] Error generating original post: %s", handle, e)

            last_post_times[handle] = now

        # Sleep between cycles
        if not _shutdown:
            time.sleep(CYCLE_SLEEP_SECONDS)

    log.info("=" * 60)
    log.info("Bot daemon shut down gracefully.")
    log.info("=" * 60)


if __name__ == "__main__":
    # Ensure UTF-8 output on Windows
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass

    main()

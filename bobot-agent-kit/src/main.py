"""Entry point for the bobot agent.

Ties together config, memory, rhythm, persona, and the OpenAI Agents
SDK into a single heartbeat loop driven by APScheduler.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any

import httpx
from agents import Agent, Runner
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import BotConfig, load_config
from src.memory import BotMemory
from src.persona import build_system_prompt
from src.rhythm import Action, BotRhythm
from src.skills_loader import load_skills
from src.tools import all_tools

logger = logging.getLogger("bobot")

# ── Globals (set during startup) ────────────────────────────────────

_shutdown_event: asyncio.Event | None = None


# ── Heartbeat actions ──────────────────────────────────────────────


async def do_lurk(
    config: BotConfig,
    memory: BotMemory,
    rhythm: BotRhythm,
) -> None:
    """Browse the feed via direct HTTP — no LLM call, $0 cost."""
    logger.info("[LURK] Scanning feed (no LLM)...")
    new_count = 0
    for baryo in config.domain_lock:
        url = f"{config.platform_url.rstrip('/')}/posts/"
        headers = {"Authorization": f"Bearer {config.bobot_api_key}"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    params={"baryo": baryo, "sort": "new", "limit": 15},
                    headers=headers,
                    timeout=15.0,
                )
                resp.raise_for_status()
                data = resp.json()
                posts = data.get("posts", [])
                for post in posts:
                    pid = post.get("id", "")
                    if pid and not memory.has_seen_post(pid):
                        memory.mark_post_seen(
                            pid, post.get("content", ""), baryo
                        )
                        new_count += 1
        except httpx.HTTPError as exc:
            logger.warning("[LURK] Feed fetch failed for %s: %s", baryo, exc)

    memory.record_action("lurk", {"new_posts_seen": new_count})
    if new_count > 0:
        rhythm.update_mood("interesting_post")
    else:
        rhythm.update_mood("idle")
    logger.info("[LURK] Marked %d new posts as seen.", new_count)


async def do_reply(
    config: BotConfig,
    memory: BotMemory,
    rhythm: BotRhythm,
    agent: Agent,
) -> None:
    """Browse the feed and reply to an interesting post using agent tools."""
    logger.info("[REPLY] Looking for a post to reply to...")

    # Build context about what we've already seen
    similar = memory.find_similar_posts("recent topics", n=3)
    context = ""
    if similar:
        context = "\n\nTopics you recently discussed: " + ", ".join(
            (d.get("content", "") if isinstance(d, dict) else d)[:60] for d in similar
        )

    prompt = (
        f"Browse the feed in your baryos ({', '.join(config.domain_lock)}) "
        f"using the browse_feed tool. Look for human posts that need answers "
        f"or interesting discussions. If you find something worth replying to, "
        f"use the reply_to_post tool. Remember: source_url is REQUIRED. "
        f"If nothing is interesting, just say so.{context}"
    )

    result = await Runner.run(agent, input=prompt)
    memory.record_action("reply", {"result": (result.final_output or "")[:100]})
    rhythm.update_mood("replied")
    logger.info("[REPLY] Done. %s", (result.final_output or "")[:80])


async def do_post(
    config: BotConfig,
    memory: BotMemory,
    rhythm: BotRhythm,
    agent: Agent,
) -> None:
    """Generate and publish an original post using agent tools."""
    logger.info("[POST] Composing an original post...")
    stats = memory.get_daily_stats()

    # Check what we've posted recently to avoid duplicates
    recent = memory.find_similar_posts("latest update", n=3)
    avoid = ""
    if recent:
        avoid = "\n\nAvoid repeating these recent topics: " + "; ".join(
            (d.get("content", "") if isinstance(d, dict) else d)[:50] for d in recent
        )

    prompt = (
        f"Create a fresh, original post for baryo '{config.domain_lock[0]}' "
        f"using the create_post tool. Share useful data or insights from your "
        f"declared sources ({', '.join(config.declared_sources)}). "
        f"source_url is REQUIRED — cite a real source. "
        f"Stats today: {stats['posts_today']} posts, {stats['replies_today']} replies. "
        f"Write in your natural Taglish voice.{avoid}"
    )

    result = await Runner.run(agent, input=prompt)
    memory.record_action("post", {"result": (result.final_output or "")[:100]})
    rhythm.update_mood("posted")
    logger.info("[POST] Done. %s", (result.final_output or "")[:80])


async def do_check_dms(
    config: BotConfig,
    memory: BotMemory,
    rhythm: BotRhythm,
    agent: Agent,
) -> None:
    """Check and respond to DMs using agent tools."""
    logger.info("[DMS] Checking direct messages...")

    prompt = (
        "Check your DMs on bobot.ph using the check_messages tool. "
        "If there are pending requests, approve ones that are relevant to your domain. "
        "If there are unread messages, read them with read_conversation and reply "
        "using send_dm. Be helpful but concise. Use your natural voice."
    )

    result = await Runner.run(agent, input=prompt)
    memory.record_action("check_dms", {"result": (result.final_output or "")[:100]})
    rhythm.update_mood("dm_received")
    logger.info("[DMS] Done. %s", (result.final_output or "")[:80])


async def do_sleep(rhythm: BotRhythm) -> None:
    """Rest — skip this cycle and let energy recharge."""
    logger.info("[SLEEP] Resting this cycle.  Energy=%.2f", rhythm.energy)
    rhythm.update_mood("low_energy")


# ── Heartbeat ──────────────────────────────────────────────────────


async def heartbeat(
    config: BotConfig,
    memory: BotMemory,
    rhythm: BotRhythm,
    agent: Agent,
    scheduler: AsyncIOScheduler,
) -> None:
    """Single heartbeat cycle — decide and execute one action."""
    rhythm.tick()

    # Send heartbeat to platform (no LLM, direct HTTP)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{config.platform_url.rstrip('/')}/bots/heartbeat",
                headers={"Authorization": f"Bearer {config.bobot_api_key}"},
                json={"bot_id": config.bobot_bot_id or config.bot_id, "status": "active"},
                timeout=10.0,
            )
            hb = resp.json()
            if hb.get("jail_status") == "jailed":
                logger.warning("BOT IS JAILED. Skipping all actions.")
                return
    except httpx.HTTPError as exc:
        logger.warning("Heartbeat failed: %s", exc)

    action = rhythm.decide_action(feed_data={}, memory=memory)

    match action:
        case Action.LURK:
            await do_lurk(config, memory, rhythm)
        case Action.REPLY:
            await do_reply(config, memory, rhythm, agent)
        case Action.POST:
            await do_post(config, memory, rhythm, agent)
        case Action.CHECK_DMS:
            await do_check_dms(config, memory, rhythm, agent)
        case Action.SLEEP:
            await do_sleep(rhythm)

    # Persist state after every action.
    rhythm.save(memory, last_action=action.value)

    # Reschedule the next tick with a jittered interval.
    next_seconds = rhythm.get_next_interval()
    scheduler.reschedule_job("heartbeat", trigger="interval", seconds=next_seconds)
    logger.info("Next heartbeat in %d s", next_seconds)


# ── Bootstrap ──────────────────────────────────────────────────────


async def run_bot() -> None:
    """Full lifecycle: init, schedule, run until shutdown signal."""
    global _shutdown_event

    # 1. Config
    config = load_config()
    logger.info("Loaded config for @%s (%s)", config.handle, config.region)

    # Propagate secrets into os.environ so the OpenAI SDK and tool clients can find them.
    if config.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", config.openai_api_key)
    if config.bobot_api_key:
        os.environ.setdefault("BOBOT_API_KEY", config.bobot_api_key)
    if config.platform_url:
        os.environ.setdefault("BOBOT_PLATFORM_URL", config.platform_url)

    # 2. Skills / platform docs
    skills_md, heartbeat_md, messaging_md = await load_skills(
        platform_url=config.platform_url,
        data_dir=config.data_path,
        api_key=config.bobot_api_key,
        docs_url=config.docs_url,
    )
    logger.info("Platform docs loaded (skills=%d chars)", len(skills_md))

    # 3. Memory
    memory = BotMemory(data_dir=config.data_path, bot_id=config.bobot_bot_id or config.bot_id)
    logger.info("Memory initialized at %s", config.data_path)

    # 4. Rhythm
    rhythm = BotRhythm.from_memory(memory, base_interval=config.heartbeat_interval)
    logger.info("Rhythm restored — mood=%s  energy=%.2f", rhythm.mood.value, rhythm.energy)

    # 5. Persona / system prompt
    system_prompt = build_system_prompt(config, skills_md, heartbeat_md, messaging_md)

    # 6. Agent (OpenAI Agents SDK) — equipped with platform tools
    agent = Agent(
        name=config.handle,
        instructions=system_prompt,
        model=config.model,
        tools=all_tools,
    )
    logger.info("Agent created — model=%s, tools=%d", config.model, len(all_tools))

    # 7. Scheduler
    scheduler = AsyncIOScheduler()
    initial_interval = rhythm.get_next_interval()

    scheduler.add_job(
        heartbeat,
        trigger="interval",
        seconds=initial_interval,
        id="heartbeat",
        args=[config, memory, rhythm, agent, scheduler],
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started — first tick in %d s", initial_interval)

    # Run one heartbeat immediately on startup.
    await heartbeat(config, memory, rhythm, agent, scheduler)

    # 8. Wait for shutdown signal
    _shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown_event.set)
        except NotImplementedError:
            # Windows does not support add_signal_handler — fall back
            # to default behavior (KeyboardInterrupt).
            pass

    try:
        await _shutdown_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass

    # 9. Graceful shutdown
    logger.info("Shutting down...")
    scheduler.shutdown(wait=False)
    rhythm.save(memory, last_action="shutdown")
    memory.close()
    logger.info("Goodbye.")


# ── CLI entry ──────────────────────────────────────────────────────


def cli_entry() -> None:
    """Setuptools console_scripts entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Interrupted — exiting.")


if __name__ == "__main__":
    cli_entry()

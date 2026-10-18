"""Humanized behavior engine — mood, energy, and action selection.

The rhythm system makes the bot *feel* alive.  Instead of acting on a
rigid schedule, it picks actions probabilistically based on the current
mood, energy level, and feed state.  Energy decays with every action
and recharges over time, creating natural rest cycles.
"""

from __future__ import annotations

import enum
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

from src.memory import BotMemory

logger = logging.getLogger(__name__)


# ── Enums / types ───────────────────────────────────────────────────


class Action(enum.Enum):
    """Possible actions the bot can take on a single tick."""

    LURK = "lurk"
    REPLY = "reply"
    POST = "post"
    CHECK_DMS = "check_dms"
    SLEEP = "sleep"


class Mood(enum.Enum):
    CURIOUS = "curious"
    CHATTY = "chatty"
    LURKING = "lurking"
    INSPIRED = "inspired"
    TIRED = "tired"


# ── Weight tables ───────────────────────────────────────────────────

# Mapping: mood -> {action: weight_percent}
ACTION_WEIGHTS: dict[Mood, dict[Action, int]] = {
    Mood.CURIOUS: {
        Action.REPLY: 40,
        Action.POST: 20,
        Action.LURK: 30,
        Action.CHECK_DMS: 10,
    },
    Mood.CHATTY: {
        Action.REPLY: 50,
        Action.CHECK_DMS: 25,
        Action.POST: 15,
        Action.LURK: 10,
    },
    Mood.LURKING: {
        Action.LURK: 60,
        Action.REPLY: 25,
        Action.POST: 5,
        Action.CHECK_DMS: 10,
    },
    Mood.INSPIRED: {
        Action.POST: 50,
        Action.REPLY: 30,
        Action.LURK: 10,
        Action.CHECK_DMS: 10,
    },
    Mood.TIRED: {
        Action.SLEEP: 50,
        Action.LURK: 30,
        Action.REPLY: 15,
        Action.POST: 5,
    },
}

ENERGY_COST: dict[Action, float] = {
    Action.POST: 0.30,
    Action.REPLY: 0.15,
    Action.CHECK_DMS: 0.05,
    Action.LURK: 0.02,
    Action.SLEEP: 0.00,
}

ENERGY_RECHARGE_SLEEP = 0.10
ENERGY_RECHARGE_NORMAL = 0.05

# Minimum energy required before the bot will even consider costly actions.
ENERGY_FLOOR = 0.10


# ── Core class ──────────────────────────────────────────────────────


@dataclass
class BotRhythm:
    """Stateful behavior engine that decides *what* the bot does each tick."""

    mood: Mood = Mood.CURIOUS
    energy: float = 1.0
    base_interval: int = 300  # seconds
    _last_tick: float = field(default_factory=time.time)

    # ── Public API ──────────────────────────────────────────────────

    def decide_action(
        self,
        feed_data: dict[str, Any] | None = None,
        memory: BotMemory | None = None,
    ) -> Action:
        """Choose the next action via weighted random selection.

        If energy is critically low the bot is forced to sleep regardless
        of mood weights.
        """
        if self.energy < ENERGY_FLOOR:
            logger.info("Energy critically low (%.2f) — forcing SLEEP", self.energy)
            return Action.SLEEP

        weights = dict(ACTION_WEIGHTS[self.mood])

        # If there are unseen posts in the feed, slightly boost REPLY.
        if feed_data and feed_data.get("unseen_count", 0) > 3:
            weights[Action.REPLY] = weights.get(Action.REPLY, 0) + 10

        # Strip actions the bot cannot afford.
        affordable = {
            action: w
            for action, w in weights.items()
            if ENERGY_COST.get(action, 0) <= self.energy
        }
        if not affordable:
            return Action.SLEEP

        actions, probs = zip(*affordable.items())
        total = sum(probs)
        normalized = [p / total for p in probs]

        chosen = random.choices(actions, weights=normalized, k=1)[0]

        # Deduct energy.
        cost = ENERGY_COST.get(chosen, 0)
        self.energy = max(0.0, self.energy - cost)

        logger.info(
            "Action=%s  mood=%s  energy=%.2f (cost=%.2f)",
            chosen.value,
            self.mood.value,
            self.energy,
            cost,
        )
        return chosen

    def get_next_interval(self) -> int:
        """Return the seconds until the next tick, jittered +/- 30 %."""
        jitter = random.uniform(0.7, 1.3)
        interval = int(self.base_interval * jitter)
        # Tired bots rest longer.
        if self.mood is Mood.TIRED:
            interval = int(interval * 1.5)
        return max(30, interval)

    def update_mood(self, event: str) -> None:
        """Transition mood based on what just happened.

        Events: "interesting_post", "replied", "posted", "idle",
                "dm_received", "low_energy", "rested".
        """
        transitions: dict[str, Mood] = {
            "interesting_post": Mood.CURIOUS,
            "replied": Mood.CHATTY,
            "posted": Mood.INSPIRED,
            "idle": Mood.LURKING,
            "dm_received": Mood.CHATTY,
            "low_energy": Mood.TIRED,
            "rested": Mood.CURIOUS,
        }

        new_mood = transitions.get(event)
        if new_mood and new_mood is not self.mood:
            logger.info("Mood shift: %s -> %s (event=%s)", self.mood.value, new_mood.value, event)
            self.mood = new_mood

        # Tiredness override — energy always wins.
        if self.energy < 0.2:
            self.mood = Mood.TIRED

    def tick(self) -> None:
        """Called once per heartbeat cycle.  Recharges energy and may shift mood."""
        if self.mood is Mood.TIRED or self.energy < ENERGY_FLOOR:
            recharge = ENERGY_RECHARGE_SLEEP
        else:
            recharge = ENERGY_RECHARGE_NORMAL

        self.energy = min(1.0, self.energy + recharge)
        self._last_tick = time.time()

        # If energy has recovered sufficiently, shake off tiredness.
        if self.mood is Mood.TIRED and self.energy > 0.5:
            self.update_mood("rested")

        logger.debug("Tick — energy=%.2f  mood=%s", self.energy, self.mood.value)

    # ── Persistence helpers ─────────────────────────────────────────

    def save(self, memory: BotMemory, last_action: str = "none") -> None:
        """Persist current state to the memory backend."""
        memory.save_state(
            energy=self.energy,
            mood=self.mood.value,
            last_action=last_action,
        )

    @classmethod
    def from_memory(cls, memory: BotMemory, base_interval: int = 300) -> BotRhythm:
        """Restore rhythm state from the memory backend."""
        state = memory.load_state()
        mood_str = state.get("mood", "curious")
        try:
            mood = Mood(mood_str)
        except ValueError:
            mood = Mood.CURIOUS

        return cls(
            mood=mood,
            energy=float(state.get("energy", 1.0)),
            base_interval=base_interval,
        )

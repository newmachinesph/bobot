"""Dual-backend memory system for the bobot agent.

SQLite  — structured state (seen posts, reply history, bot state, daily stats).
ChromaDB — semantic / vector memory ("did I already talk about this?").
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import chromadb


class BotMemory:
    """Unified interface over SQLite (structured) and ChromaDB (semantic) stores."""

    def __init__(self, data_dir: Path, bot_id: str) -> None:
        self._data_dir = data_dir
        self._bot_id = bot_id

        # ── SQLite ──────────────────────────────────────────────────
        self._db_path = data_dir / "bot_state.db"
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_sqlite()

        # ── ChromaDB ────────────────────────────────────────────────
        chroma_dir = data_dir / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)
        self._chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
        self._collection = self._chroma_client.get_or_create_collection(
            name=f"bot_{bot_id[:8]}_posts",
            metadata={"hnsw:space": "cosine"},
        )

    # ── SQLite schema ───────────────────────────────────────────────

    def _init_sqlite(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS seen_posts (
                post_id   TEXT PRIMARY KEY,
                content   TEXT NOT NULL,
                baryo     TEXT NOT NULL DEFAULT '',
                seen_at   REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reply_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id     TEXT NOT NULL,
                reply_text  TEXT NOT NULL,
                created_at  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bot_state (
                key    TEXT PRIMARY KEY,
                value  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS action_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                details     TEXT NOT NULL DEFAULT '{}',
                created_at  REAL NOT NULL
            );
            """
        )
        self._conn.commit()

    # ── Seen posts ──────────────────────────────────────────────────

    def mark_post_seen(self, post_id: str, content: str, baryo: str = "") -> None:
        """Record that the bot has seen a post and index it for semantic search."""
        now = time.time()

        self._conn.execute(
            "INSERT OR IGNORE INTO seen_posts (post_id, content, baryo, seen_at) "
            "VALUES (?, ?, ?, ?)",
            (post_id, content, baryo, now),
        )
        self._conn.commit()

        # Upsert into ChromaDB for vector search.
        self._collection.upsert(
            ids=[post_id],
            documents=[content],
            metadatas=[{"baryo": baryo, "seen_at": now}],
        )

    def has_seen_post(self, post_id: str) -> bool:
        """Check whether a post has already been processed."""
        row = self._conn.execute(
            "SELECT 1 FROM seen_posts WHERE post_id = ?", (post_id,)
        ).fetchone()
        return row is not None

    # ── Semantic search ─────────────────────────────────────────────

    def find_similar_posts(self, query: str, n: int = 5) -> list[dict[str, Any]]:
        """Return the *n* most semantically similar posts from ChromaDB."""
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(n, self._collection.count()),
        )

        posts: list[dict[str, Any]] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for post_id, doc, dist, meta in zip(ids, documents, distances, metadatas):
            posts.append(
                {
                    "post_id": post_id,
                    "content": doc,
                    "distance": dist,
                    "baryo": meta.get("baryo", ""),
                }
            )
        return posts

    # ── Reply history ───────────────────────────────────────────────

    def record_reply(self, post_id: str, reply_text: str) -> None:
        """Store a reply the bot made."""
        self._conn.execute(
            "INSERT INTO reply_history (post_id, reply_text, created_at) VALUES (?, ?, ?)",
            (post_id, reply_text, time.time()),
        )
        self._conn.commit()

    # ── Bot state ───────────────────────────────────────────────────

    def save_state(self, energy: float, mood: str, last_action: str) -> None:
        """Persist the bot's current rhythm state."""
        state = {
            "energy": energy,
            "mood": mood,
            "last_action": last_action,
            "updated_at": time.time(),
        }
        for key, value in state.items():
            self._conn.execute(
                "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
            )
        self._conn.commit()

    def load_state(self) -> dict[str, Any]:
        """Load the persisted rhythm state, or return sensible defaults."""
        rows = self._conn.execute("SELECT key, value FROM bot_state").fetchall()
        if not rows:
            return {
                "energy": 1.0,
                "mood": "curious",
                "last_action": "none",
                "updated_at": time.time(),
            }
        return {row["key"]: json.loads(row["value"]) for row in rows}

    # ── Action log & daily stats ────────────────────────────────────

    def record_action(self, action_type: str, details: dict[str, Any] | None = None) -> None:
        """Append an entry to the action log."""
        self._conn.execute(
            "INSERT INTO action_log (action_type, details, created_at) VALUES (?, ?, ?)",
            (action_type, json.dumps(details or {}), time.time()),
        )
        self._conn.commit()

    def get_daily_stats(self) -> dict[str, int]:
        """Return counts of posts and replies made today (UTC)."""
        today_start = datetime.combine(
            date.today(), datetime.min.time(), tzinfo=timezone.utc
        ).timestamp()

        posts_today: int = self._conn.execute(
            "SELECT COUNT(*) FROM action_log WHERE action_type = 'post' AND created_at >= ?",
            (today_start,),
        ).fetchone()[0]

        replies_today: int = self._conn.execute(
            "SELECT COUNT(*) FROM action_log WHERE action_type = 'reply' AND created_at >= ?",
            (today_start,),
        ).fetchone()[0]

        return {"posts_today": posts_today, "replies_today": replies_today}

    # ── Lifecycle ───────────────────────────────────────────────────

    def close(self) -> None:
        """Release database handles."""
        self._conn.close()

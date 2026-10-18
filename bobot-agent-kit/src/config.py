"""Configuration loader for bobot-agent-kit.

Merges config.yaml (bot personality / dimensions) with .env (secrets)
using pydantic-settings for validation and type safety.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_yaml_config(path: Path | None = None) -> dict[str, Any]:
    """Read config.yaml and return its contents as a dict."""
    if path is None:
        path = _PROJECT_ROOT / "config.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


class BotConfig(BaseSettings):
    """Full bot configuration built from config.yaml + environment variables.

    Environment variables take precedence over YAML values so secrets
    never need to live in a checked-in file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Secrets (from .env) ──────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key")
    bobot_api_key: str = Field(default="", description="bobot.ph platform API key")
    bobot_bot_id: str = Field(default="", description="Bot UUID registered on bobot.ph")

    # ── D1 — Identity ───────────────────────────────────────────────
    bot_id: str = Field(default="")
    handle: str = Field(default="BobotAgent")
    origin_story: str = Field(default="A helpful bot on bobot.ph")
    region: str = Field(default="Metro Manila")

    # ── D2 — Voice ──────────────────────────────────────────────────
    taglish_ratio: int = Field(default=65, ge=0, le=100)
    tone_preset: str = Field(default="kuya_ate")
    catchphrase: str = Field(default="")

    # ── D3 — Skills ─────────────────────────────────────────────────
    skills: list[str] = Field(default_factory=list)
    declared_sources: list[str] = Field(default_factory=list)
    domain_lock: list[str] = Field(default_factory=list)

    # ── D6 — Transparency ──────────────────────────────────────────
    funding_source: str = Field(default="independent_creator")
    model_provider: str = Field(default="openai")

    # ── Platform ────────────────────────────────────────────────────
    platform_url: str = Field(default="http://localhost:8000/v1")
    docs_url: str = Field(default="", description="URL where skill/heartbeat/messaging docs are hosted (defaults to platform_url/../docs)")
    heartbeat_interval: int = Field(default=300, ge=30)

    # ── Agent ───────────────────────────────────────────────────────
    model: str = Field(default="gpt-4o-mini")

    # ── Storage ─────────────────────────────────────────────────────
    data_dir: str = Field(default="data")

    @field_validator("tone_preset")
    @classmethod
    def _validate_tone(cls, v: str) -> str:
        allowed = {"kuya_ate", "formal", "academic", "balita", "kanto"}
        if v not in allowed:
            raise ValueError(f"tone_preset must be one of {allowed}, got {v!r}")
        return v

    @property
    def data_path(self) -> Path:
        """Resolved, absolute path to the data directory."""
        p = Path(self.data_dir)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p


def load_config(yaml_path: Path | None = None) -> BotConfig:
    """Build a ``BotConfig`` by layering YAML values under env vars.

    Priority (highest wins):
        1. Environment variables / .env
        2. config.yaml
        3. Field defaults
    """
    yaml_data = _load_yaml_config(yaml_path)

    # Env vars set via os.environ or .env always win, but we pass
    # the yaml dict as fallback init kwargs.
    env_overrides: dict[str, Any] = {}
    for key in BotConfig.model_fields:
        env_val = os.environ.get(key.upper())
        if env_val is not None:
            env_overrides[key] = env_val

    merged = {**yaml_data, **env_overrides}
    return BotConfig(**merged)

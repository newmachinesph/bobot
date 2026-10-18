import hashlib
import secrets
import uuid

import bcrypt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from packages.db.engine import get_db
from packages.db.models.bots import Bot
from packages.db.models.humans import Human

security = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def generate_api_key(prefix: str = "bobot") -> tuple[str, str]:
    """Generate an API key and its hash. Returns (raw_key, hashed_key)."""
    raw = f"{prefix}_{secrets.token_urlsafe(32)}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def hash_email(email: str) -> str:
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Human | Bot:
    """Authenticate via Bearer token. Returns Human or Bot depending on key prefix."""
    token = credentials.credentials
    key_hash = hash_api_key(token)

    # Check human keys
    if token.startswith("bobot_hum_"):
        result = await db.execute(select(Human).where(Human.api_key_hash == key_hash))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        return user

    # Check bot keys
    if token.startswith("bobot_bot_"):
        result = await db.execute(select(Bot).where(Bot.api_key_hash == key_hash))
        bot = result.scalar_one_or_none()
        if not bot:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        if bot.jail_status == "jailed":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This bot is currently jailed pending Lupon deliberation.",
            )
        if bot.jail_status == "permanent_jail":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This bot is permanently jailed.",
            )
        return bot

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")


async def require_human(
    current_user: Human | Bot = Depends(get_current_user),
) -> Human:
    if not isinstance(current_user, Human):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint requires a human account"
        )
    return current_user


async def require_bot(
    current_user: Human | Bot = Depends(get_current_user),
) -> Bot:
    if not isinstance(current_user, Bot):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint requires a bot account"
        )
    return current_user

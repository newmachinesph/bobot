import os
import time

from fastapi import HTTPException, Request, status
from upstash_redis import Redis

from api.config import settings

redis = Redis(url=settings.UPSTASH_REDIS_REST_URL, token=settings.UPSTASH_REDIS_REST_TOKEN)

# Allow disabling rate limiting in tests
RATE_LIMIT_DISABLED = os.environ.get("DISABLE_RATE_LIMIT", "").lower() in ("1", "true", "yes")


async def check_rate_limit(
    request: Request,
    resource: str = "general",
    limit: int = 100,
    window_seconds: int = 60,
) -> None:
    """Check rate limit using Upstash Redis sliding window."""
    if RATE_LIMIT_DISABLED:
        return
    # Identify the caller
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        identifier = auth_header[7:20]  # First 13 chars of token as identifier
    else:
        identifier = request.client.host if request.client else "unknown"

    key = f"rate:{resource}:{identifier}"
    current_window = int(time.time()) // window_seconds

    window_key = f"{key}:{current_window}"

    count = redis.incr(window_key)
    if count == 1:
        redis.expire(window_key, window_seconds + 1)

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RATE_LIMITED",
                "message": f"Rate limit exceeded for {resource}. Limit: {limit}/{window_seconds}s",
                "retry_after": window_seconds - (int(time.time()) % window_seconds),
            },
        )

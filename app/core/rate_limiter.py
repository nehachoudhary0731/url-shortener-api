from fastapi import HTTPException, Request
from app.core.redis_client import redis_client
from app.core.config import settings


def rate_limit(request: Request):
    """
    Sliding window rate limiter using Redis.
    Allows RATE_LIMIT_PER_MINUTE requests per IP per minute.
    """
    ip = request.client.host
    key = f"rate_limit:{ip}"

    current = redis_client.get(key)
    if current is None:
        redis_client.setex(key, 60, 1)
    elif int(current) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {settings.RATE_LIMIT_PER_MINUTE} requests per minute."
        )
    else:
        redis_client.incr(key)

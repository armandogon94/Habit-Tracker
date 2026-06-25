"""Async Redis client.

A single, lazily-created client shared across requests — used for the
refresh-token whitelist (and future caching). Tests override the FastAPI
``get_redis`` dependency with a fakeredis instance, so this module is never
hit under test.
"""

from redis.asyncio import Redis, from_url

from app.core.config import settings

_client: Redis | None = None


def get_redis_client() -> Redis:
    """Return the process-wide async Redis client (created on first use)."""
    global _client
    if _client is None:
        _client = from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def get_redis() -> Redis:
    """FastAPI dependency yielding the shared async Redis client."""
    return get_redis_client()


async def close_redis() -> None:
    """Close the shared client (called on app shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

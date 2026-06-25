"""Redis-backed refresh-token whitelist.

A refresh token is only honoured if its ``jti`` is present here. Rotation
revokes the presented jti and adds a fresh one; logout revokes the jti;
replaying an already-rotated jti is treated as theft and revokes every session
for the user (RFC 6819 refresh-token reuse detection).

Keys (all carry the refresh-token TTL):
    refresh:{jti}          -> user_id    (the whitelist entry)
    refresh_user:{user_id} -> set[jti]   (index so we can revoke all at once)
"""

from uuid import UUID

from redis.asyncio import Redis


def _jti_key(jti: str) -> str:
    return f"refresh:{jti}"


def _user_key(user_id: UUID | str) -> str:
    return f"refresh_user:{user_id}"


async def add(redis: Redis, jti: str, user_id: UUID | str, ttl_seconds: int) -> None:
    """Whitelist ``jti`` for ``user_id`` with the given TTL."""
    await redis.set(_jti_key(jti), str(user_id), ex=ttl_seconds)
    await redis.sadd(_user_key(user_id), jti)
    await redis.expire(_user_key(user_id), ttl_seconds)


async def is_valid(redis: Redis, jti: str, user_id: UUID | str) -> bool:
    """True only if ``jti`` is whitelisted AND bound to ``user_id``."""
    stored = await redis.get(_jti_key(jti))
    return stored is not None and stored == str(user_id)


async def revoke(redis: Redis, jti: str, user_id: UUID | str | None = None) -> None:
    """Remove a single ``jti`` from the whitelist."""
    await redis.delete(_jti_key(jti))
    if user_id is not None:
        await redis.srem(_user_key(user_id), jti)


async def revoke_all_for_user(redis: Redis, user_id: UUID | str) -> None:
    """Revoke every whitelisted refresh token for a user (reuse detection)."""
    jtis = await redis.smembers(_user_key(user_id))
    keys = [_jti_key(j) for j in jtis]
    if keys:
        await redis.delete(*keys)
    await redis.delete(_user_key(user_id))

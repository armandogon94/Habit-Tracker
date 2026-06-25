import pytest
from fakeredis.aioredis import FakeRedis

from app.services import refresh_whitelist


@pytest.fixture
async def r():
    client = FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


async def test_add_then_is_valid(r):
    await refresh_whitelist.add(r, "jti1", "user1", 60)
    assert await refresh_whitelist.is_valid(r, "jti1", "user1") is True


async def test_is_valid_false_for_unknown_jti(r):
    assert await refresh_whitelist.is_valid(r, "missing", "user1") is False


async def test_is_valid_false_for_wrong_user(r):
    await refresh_whitelist.add(r, "jti1", "user1", 60)
    assert await refresh_whitelist.is_valid(r, "jti1", "user2") is False


async def test_revoke_makes_invalid(r):
    await refresh_whitelist.add(r, "jti1", "user1", 60)
    await refresh_whitelist.revoke(r, "jti1", "user1")
    assert await refresh_whitelist.is_valid(r, "jti1", "user1") is False


async def test_revoke_all_for_user_leaves_other_users(r):
    await refresh_whitelist.add(r, "a", "user1", 60)
    await refresh_whitelist.add(r, "b", "user1", 60)
    await refresh_whitelist.add(r, "c", "user2", 60)
    await refresh_whitelist.revoke_all_for_user(r, "user1")
    assert await refresh_whitelist.is_valid(r, "a", "user1") is False
    assert await refresh_whitelist.is_valid(r, "b", "user1") is False
    assert await refresh_whitelist.is_valid(r, "c", "user2") is True


async def test_add_sets_ttl(r):
    await refresh_whitelist.add(r, "jti1", "user1", 60)
    ttl = await r.ttl("refresh:jti1")
    assert 0 < ttl <= 60


async def test_consume_returns_true_and_revokes(r):
    await refresh_whitelist.add(r, "jti1", "user1", 60)
    assert await refresh_whitelist.consume(r, "jti1", "user1") is True
    assert await refresh_whitelist.is_valid(r, "jti1", "user1") is False


async def test_consume_is_atomic_only_first_wins(r):
    # The TOCTOU guard: two consumes of the same jti -> exactly one succeeds.
    await refresh_whitelist.add(r, "jti1", "user1", 60)
    first = await refresh_whitelist.consume(r, "jti1", "user1")
    second = await refresh_whitelist.consume(r, "jti1", "user1")
    assert first is True
    assert second is False


async def test_consume_false_for_wrong_user(r):
    await refresh_whitelist.add(r, "jti1", "user1", 60)
    assert await refresh_whitelist.consume(r, "jti1", "user2") is False

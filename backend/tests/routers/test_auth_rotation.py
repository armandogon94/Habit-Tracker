import asyncio
from uuid import UUID

import pytest

from app.core.security import create_refresh_token, decode_token
from app.services import refresh_whitelist

USER_ID = "11111111-1111-1111-1111-111111111111"


class _FakeUser:
    def __init__(self, uid: str):
        self.id = UUID(uid)
        self.email = "u@example.com"
        self.timezone = "UTC"


@pytest.fixture(autouse=True)
def _patch_user_lookup(monkeypatch):
    async def _get_user_by_id(db, user_id):
        return _FakeUser(USER_ID) if str(user_id) == USER_ID else None

    monkeypatch.setattr("app.routers.auth.get_user_by_id", _get_user_by_id)


async def test_refresh_rotates_and_old_token_is_rejected(client, fake_redis):
    jti = "jti-original"
    await refresh_whitelist.add(fake_redis, jti, USER_ID, 3600)
    old_token = create_refresh_token(USER_ID, jti)

    cookie = {"Cookie": f"refresh_token={old_token}"}
    client.cookies.clear()
    resp = await client.post("/api/v1/auth/refresh", headers=cookie)
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    # The presented jti is revoked after rotation.
    assert await refresh_whitelist.is_valid(fake_redis, jti, USER_ID) is False

    # Replaying the now-rotated token is rejected.
    client.cookies.clear()
    replay = await client.post("/api/v1/auth/refresh", headers=cookie)
    assert replay.status_code == 401


async def test_refresh_reuse_revokes_all_sessions(client, fake_redis):
    # Two live sessions for the same user.
    await refresh_whitelist.add(fake_redis, "jti-a", USER_ID, 3600)
    await refresh_whitelist.add(fake_redis, "jti-b", USER_ID, 3600)
    stale_token = create_refresh_token(USER_ID, "jti-already-rotated")  # not whitelisted

    client.cookies.clear()
    resp = await client.post(
        "/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={stale_token}"}
    )
    assert resp.status_code == 401
    # Reuse detection revokes every session for the user.
    assert await refresh_whitelist.is_valid(fake_redis, "jti-a", USER_ID) is False
    assert await refresh_whitelist.is_valid(fake_redis, "jti-b", USER_ID) is False


async def test_logout_revokes_the_jti(client, fake_redis):
    jti = "jti-logout"
    await refresh_whitelist.add(fake_redis, jti, USER_ID, 3600)
    token = create_refresh_token(USER_ID, jti)

    client.cookies.clear()
    resp = await client.post("/api/v1/auth/logout", headers={"Cookie": f"refresh_token={token}"})
    assert resp.status_code == 200
    assert await refresh_whitelist.is_valid(fake_redis, jti, USER_ID) is False


def _refresh_without_jti(user_id: str) -> str:
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.core.config import settings

    return jwt.encode(
        {"sub": user_id, "type": "refresh", "exp": datetime.now(UTC) + timedelta(days=1)},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


async def test_concurrent_refresh_only_one_wins(client, fake_redis):
    # The atomic-consume guard at the HTTP layer: two refreshes of the SAME token
    # fired concurrently must yield exactly one 200 and one 401 (no session fork).
    jti = "jti-concurrent"
    await refresh_whitelist.add(fake_redis, jti, USER_ID, 3600)
    token = create_refresh_token(USER_ID, jti)
    cookie = {"Cookie": f"refresh_token={token}"}
    client.cookies.clear()
    r1, r2 = await asyncio.gather(
        client.post("/api/v1/auth/refresh", headers=cookie),
        client.post("/api/v1/auth/refresh", headers=cookie),
    )
    assert sorted([r1.status_code, r2.status_code]) == [200, 401]


async def test_login_issues_whitelisted_jti_and_cookie_drives_refresh(
    client, fake_redis, monkeypatch
):
    async def _auth(db, email, password):
        return _FakeUser(USER_ID)

    monkeypatch.setattr("app.routers.auth.authenticate_user", _auth)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "u@example.com", "password": "password1"}
    )
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    token = set_cookie.split("refresh_token=")[1].split(";")[0]
    payload = decode_token(token)
    assert await refresh_whitelist.is_valid(fake_redis, payload["jti"], USER_ID) is True

    client.cookies.clear()
    again = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={token}"})
    assert again.status_code == 200


async def test_refresh_without_cookie_is_401(client):
    client.cookies.clear()
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


async def test_refresh_with_no_jti_is_401_without_revoking_all(client, fake_redis):
    await refresh_whitelist.add(fake_redis, "live-jti", USER_ID, 3600)
    token = _refresh_without_jti(USER_ID)
    client.cookies.clear()
    resp = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={token}"})
    assert resp.status_code == 401
    # A malformed (jti-less) token must NOT nuke the live session.
    assert await refresh_whitelist.is_valid(fake_redis, "live-jti", USER_ID) is True


async def test_refresh_returns_503_when_redis_unavailable(client):
    from redis.exceptions import ConnectionError as RedisConnError

    from app.core.redis_client import get_redis
    from app.main import app

    class _BrokenRedis:
        async def getdel(self, *args, **kwargs):
            raise RedisConnError("redis down")

        async def get(self, *args, **kwargs):
            raise RedisConnError("redis down")

    async def _broken():
        return _BrokenRedis()

    app.dependency_overrides[get_redis] = _broken
    token = create_refresh_token(USER_ID, "any-jti")
    client.cookies.clear()
    resp = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={token}"})
    assert resp.status_code == 503

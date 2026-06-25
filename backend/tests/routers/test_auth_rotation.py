from uuid import UUID

import pytest

from app.core.security import create_refresh_token
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

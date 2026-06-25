"""Tests for auth dependencies that reject bad tokens before touching the DB.

All cases here fail authentication before any database access, so they pass
``db=None`` — the query is never reached.
"""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps import get_current_user
from app.core.security import create_access_token


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class _UnusedDB:
    """A DB stub whose execute() must never be called for a rejected token."""

    async def execute(self, *args, **kwargs):
        raise AssertionError("db.execute should not be reached for an invalid token")


class TestGetCurrentUser:
    async def test_missing_credentials_is_401(self):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=None, db=None)
        assert exc.value.status_code == 401

    async def test_garbage_token_is_401(self):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=_creds("not.a.jwt"), db=None)
        assert exc.value.status_code == 401

    async def test_malformed_sub_is_401_not_500(self):
        # A token that decodes cleanly but carries a non-UUID `sub` must be a
        # 401, not an unhandled ValueError -> 500 from UUID(user_id).
        token = create_access_token("not-a-valid-uuid")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=_creds(token), db=_UnusedDB())
        assert exc.value.status_code == 401

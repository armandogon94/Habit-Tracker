"""Unit tests for password hashing and JWT decoding.

These exercise app.core.security directly. They need no database; the only
external dependency is settings.JWT_SECRET, which resolves to a usable value.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def _encode(claims: dict) -> str:
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _ts(delta: timedelta) -> int:
    return int((datetime.now(UTC) + delta).timestamp())


class TestPasswordHashing:
    def test_normal_password_roundtrips(self):
        pw = "correct horse battery staple"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_wrong_password_is_rejected(self):
        hashed = hash_password("the right one")
        assert verify_password("the wrong one", hashed) is False

    def test_password_at_72_bytes_roundtrips(self):
        pw = "a" * 72
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_hash_rejects_password_over_72_bytes(self):
        # No silent truncation: two passwords sharing a 72-byte prefix must not
        # hash to the same value.
        with pytest.raises(ValueError):
            hash_password("a" * 73)

    def test_hash_rejects_multibyte_password_over_72_bytes(self):
        # 30 lock emoji = 120 UTF-8 bytes (only 30 characters).
        with pytest.raises(ValueError):
            hash_password("\U0001f512" * 30)

    def test_verify_returns_false_for_over_72_byte_input(self):
        hashed = hash_password("a" * 72)
        assert verify_password("a" * 100, hashed) is False

    def test_existing_short_hash_still_verifies(self):
        # Backward-compat: a hash produced by raw bcrypt (<=72 byte password)
        # must still verify after the truncation guard is added.
        pw = "legacy-password"
        legacy = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        assert verify_password(pw, legacy) is True


class TestJWTDecoding:
    def test_valid_access_token_decodes(self):
        payload = decode_token(create_access_token("user-1"))
        assert payload is not None
        assert payload["sub"] == "user-1"
        assert payload["type"] == "access"

    def test_token_without_exp_is_rejected(self):
        # A forged token with no expiry must NOT be treated as valid forever.
        token = _encode({"sub": "user-1", "type": "access"})
        assert decode_token(token) is None

    def test_expired_token_is_rejected(self):
        token = _encode({"sub": "user-1", "type": "access", "exp": _ts(timedelta(minutes=-5))})
        assert decode_token(token) is None

    def test_token_without_sub_is_rejected(self):
        token = _encode({"type": "access", "exp": _ts(timedelta(minutes=5))})
        assert decode_token(token) is None

    def test_token_without_type_is_rejected(self):
        token = _encode({"sub": "user-1", "exp": _ts(timedelta(minutes=5))})
        assert decode_token(token) is None

    def test_tampered_token_is_rejected(self):
        assert decode_token(create_access_token("user-1") + "tamper") is None

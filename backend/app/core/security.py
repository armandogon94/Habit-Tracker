from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


# bcrypt only consumes the first 72 bytes and bcrypt>=4 raises on longer input.
# Reject over-limit passwords here rather than truncating, so two passwords that
# share a 72-byte prefix can never hash/verify to the same value. The request
# schemas (app/schemas/auth.py) reject these first; this is defence-in-depth for
# any non-HTTP caller (mobile, CLI, seed scripts).
_BCRYPT_MAX_BYTES = 72


def _bcrypt_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        raise ValueError(f"password exceeds bcrypt's {_BCRYPT_MAX_BYTES}-byte limit")
    return encoded


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        encoded = _bcrypt_bytes(plain)
    except ValueError:
        # An over-limit input can never match a hash of a valid (<=72-byte)
        # password, so reject rather than raising during authentication.
        return False
    return bcrypt.checkpw(encoded, hashed.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "access"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            # Require and verify expiry so a forged token without `exp` is not
            # accepted as valid forever (python-jose only checks exp when present).
            options={"require_exp": True, "verify_exp": True},
        )
    except JWTError:
        return None

    # `sub` and `type` are mandatory for every token we issue; a token missing
    # either is malformed and must be rejected rather than trusted downstream.
    if not payload.get("sub") or not payload.get("type"):
        return None

    return payload

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


# bcrypt only consumes the first 72 bytes of the input, and bcrypt>=4 raises
# ValueError on anything longer instead of truncating. Truncate explicitly so a
# long password is hashed instead of crashing register/login with a 500.
# Existing hashes are unaffected: every stored hash came from a <=72-byte
# password (longer ones used to crash), and truncating those is a no-op.
_BCRYPT_MAX_BYTES = 72


def _bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_bcrypt_bytes(plain), hashed.encode("utf-8"))


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

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_REQUIRED = {
    "JWT_SECRET": "x" * 32,
    "DATABASE_URL": "postgresql+asyncpg://t:t@localhost:5432/t",
}


def test_production_requires_secure_cookie():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENVIRONMENT="production", COOKIE_SECURE=False, **_REQUIRED)


def test_production_with_secure_cookie_is_allowed():
    settings = Settings(_env_file=None, ENVIRONMENT="production", COOKIE_SECURE=True, **_REQUIRED)
    assert settings.COOKIE_SECURE is True


def test_development_allows_insecure_cookie():
    settings = Settings(_env_file=None, ENVIRONMENT="development", COOKIE_SECURE=False, **_REQUIRED)
    assert settings.COOKIE_SECURE is False

import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest


def test_register_rejects_password_over_72_bytes():
    with pytest.raises(ValidationError):
        RegisterRequest(email="u@example.com", password="a" * 73, timezone="UTC")


def test_register_accepts_password_at_72_bytes():
    req = RegisterRequest(email="u@example.com", password="a" * 72, timezone="UTC")
    assert req.password == "a" * 72


def test_register_rejects_multibyte_password_over_72_bytes():
    # 30 emoji = 120 UTF-8 bytes even though it is only 30 characters.
    with pytest.raises(ValidationError):
        RegisterRequest(email="u@example.com", password="😀" * 30, timezone="UTC")


def test_login_rejects_password_over_72_bytes():
    with pytest.raises(ValidationError):
        LoginRequest(email="u@example.com", password="a" * 73)


def test_register_rejects_invalid_timezone():
    with pytest.raises(ValidationError):
        RegisterRequest(email="u@example.com", password="longenough", timezone="Mars/Phobos")


def test_register_accepts_valid_iana_timezone():
    req = RegisterRequest(
        email="u@example.com", password="longenough", timezone="America/Los_Angeles"
    )
    assert req.timezone == "America/Los_Angeles"

"""Validation tests for auth request schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def _data(**override) -> dict:
    base = {"email": "user@example.com", "password": "longenough", "timezone": "UTC"}
    base.update(override)
    return base


def test_valid_request_is_accepted():
    req = RegisterRequest(**_data())
    assert req.email == "user@example.com"


def test_short_password_is_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(**_data(password="short"))


def test_overlong_password_is_rejected():
    # An unbounded password is a stored-data / hashing DoS vector; cap it.
    with pytest.raises(ValidationError):
        RegisterRequest(**_data(password="a" * 200))

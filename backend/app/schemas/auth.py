from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, EmailStr, Field, field_validator

# bcrypt only consumes the first 72 bytes; reject longer inputs rather than
# letting the hasher silently truncate (two passwords sharing a 72-byte prefix
# must not authenticate as the same password).
_BCRYPT_MAX_BYTES = 72


def _validate_password(value: str) -> str:
    if len(value.encode("utf-8")) > _BCRYPT_MAX_BYTES:
        raise ValueError(f"password must be at most {_BCRYPT_MAX_BYTES} bytes")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    timezone: str = Field(default="UTC", max_length=64)

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        return _validate_password(value)

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        # Reject invalid zones at the boundary so the timezone-aware backend
        # never stores a value it will later silently coerce to UTC.
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"invalid timezone: {value}") from exc
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=72)

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        return _validate_password(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    timezone: str

    model_config = {"from_attributes": True}

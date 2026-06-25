from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_refresh_token_payload
from app.core.ratelimit import AUTH_RATE_LIMIT, limiter
from app.core.redis_client import get_redis
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import refresh_whitelist
from app.services.auth_service import authenticate_user, get_user_by_id, register_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

REFRESH_TTL_SECONDS = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Set the refresh-token cookie with consistent, env-driven security flags."""
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=REFRESH_TTL_SECONDS,
        path="/",
    )


async def _issue_refresh(redis: Redis, response: Response, user_id: str) -> None:
    """Mint a whitelisted refresh token (new jti) and set it as the cookie."""
    jti = str(uuid4())
    token = create_refresh_token(user_id, jti)
    await refresh_whitelist.add(redis, jti, user_id, REFRESH_TTL_SECONDS)
    _set_refresh_cookie(response, token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(
    request: Request,
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    try:
        user = await register_user(db, data.email, data.password, data.timezone)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    await _issue_refresh(redis, response, str(user.id))
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request,
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    await _issue_refresh(redis, response, str(user.id))
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def refresh(
    request: Request,
    response: Response,
    payload: dict = Depends(get_refresh_token_payload),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    try:
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from None

    jti = payload.get("jti")
    # Atomically validate AND revoke the presented jti (consume). Two concurrent
    # refreshes of the same jti cannot both win, so a session can never fork.
    if not jti or not await refresh_whitelist.consume(redis, jti, user_id):
        # Absent / already-consumed jti: presenting a rotated token signals reuse
        # (RFC 6819), so revoke every session for the user.
        await refresh_whitelist.revoke_all_for_user(redis, user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # The presented jti is now consumed; issue + whitelist a fresh one.
    await _issue_refresh(redis, response, str(user.id))
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    redis: Redis = Depends(get_redis),
):
    if refresh_token:
        payload = decode_token(refresh_token)
        if payload and payload.get("jti"):
            await refresh_whitelist.revoke(redis, payload["jti"])
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(id=str(user.id), email=user.email, timezone=user.timezone)

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.ratelimit import client_ip


@pytest.fixture
def limited_app():
    app = FastAPI()
    # A fresh, isolated limiter so this test never shares state with the app's.
    test_limiter = Limiter(key_func=client_ip)
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/ping")
    @test_limiter.limit("3/minute")
    async def ping(request: Request):
        return {"ok": True}

    return app


async def test_returns_429_after_limit(limited_app):
    transport = ASGITransport(app=limited_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(3):
            assert (await client.get("/ping")).status_code == 200
        over = await client.get("/ping")
        assert over.status_code == 429


async def test_real_login_endpoint_is_rate_limited(monkeypatch):
    from fakeredis.aioredis import FakeRedis

    from app.core.ratelimit import limiter as app_limiter
    from app.core.redis_client import get_redis
    from app.database import get_db
    from app.main import app

    fake = FakeRedis(decode_responses=True)

    async def _redis():
        return fake

    async def _db():
        yield None

    async def _auth(db, email, password):
        return None  # invalid creds -> 401 each time, until the limiter trips 429

    monkeypatch.setattr("app.routers.auth.authenticate_user", _auth)
    app.dependency_overrides[get_redis] = _redis
    app.dependency_overrides[get_db] = _db
    app_limiter.enabled = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            statuses = []
            for _ in range(12):
                r = await c.post(
                    "/api/v1/auth/login",
                    json={"email": "a@b.com", "password": "password1"},
                )
                statuses.append(r.status_code)
        assert 401 in statuses  # some attempts get through
        assert 429 in statuses  # then the real /login decorator trips the limit
    finally:
        app.dependency_overrides.clear()
        app_limiter.enabled = True
        await fake.aclose()

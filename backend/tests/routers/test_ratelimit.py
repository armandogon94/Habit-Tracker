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

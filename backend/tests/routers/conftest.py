import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient

from app.core.ratelimit import limiter
from app.core.redis_client import get_redis
from app.database import get_db
from app.main import app


@pytest.fixture
async def fake_redis():
    client = FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def client(fake_redis):
    """An httpx client against the real app with Redis faked and the DB stubbed.

    Auth router tests monkeypatch the auth service functions, so the stubbed DB
    session is never used for I/O. Rate limiting is disabled here (it has its own
    test) so the shared limiter's state can't throttle these requests.
    """

    async def _override_redis():
        return fake_redis

    async def _override_db():
        yield None

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db] = _override_db
    limiter.enabled = False

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    limiter.enabled = True

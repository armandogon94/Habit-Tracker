"""Tests for the global exception handlers.

Uncaught errors must become clean JSON responses with appropriate status
codes and must not leak internal exception detail or stack traces.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import register_exception_handlers


def _make_client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom-value")
    async def boom_value():
        raise ValueError("already logged for this date")

    @app.get("/boom-integrity")
    async def boom_integrity():
        raise IntegrityError("INSERT ...", {}, Exception("duplicate key value violates unique"))

    @app.get("/boom-generic")
    async def boom_generic():
        raise RuntimeError("SECRET internal connection string leaked")

    # raise_server_exceptions=False so the 500 handler's response is returned
    # rather than the original exception being re-raised by the test client.
    return TestClient(app, raise_server_exceptions=False)


client = _make_client()


def test_value_error_becomes_400():
    r = client.get("/boom-value")
    assert r.status_code == 400
    assert "already logged" in r.json()["detail"]


def test_integrity_error_becomes_409_without_sql():
    r = client.get("/boom-integrity")
    assert r.status_code == 409
    assert "duplicate key" not in r.text  # internal DB detail not leaked


def test_generic_error_becomes_500_without_internals():
    r = client.get("/boom-generic")
    assert r.status_code == 500
    assert "SECRET internal" not in r.text  # no stack trace / internals leaked
    assert r.json()["detail"]

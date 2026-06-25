"""Application rate limiter (slowapi).

Keyed by the real client IP. Behind a reverse proxy (Traefik) the socket peer
is the proxy, so we trust the left-most ``X-Forwarded-For`` entry the proxy
sets, falling back to the socket peer for direct/local connections. (This trusts
the proxy to set/scrub that header — it must not be exposed to clients directly.)

Storage is in-process per worker; switch to a shared Redis backend when running
multiple instances. Limits are applied per-endpoint via ``@limiter.limit(...)``.
"""

from fastapi import Request
from slowapi import Limiter


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip)

# Limit on the unauthenticated/credential endpoints (login, register, refresh).
AUTH_RATE_LIMIT = "10/minute"

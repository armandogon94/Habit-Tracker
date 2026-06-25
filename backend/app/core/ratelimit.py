"""Application rate limiter (slowapi).

Keyed by the real client IP (the socket peer). We deliberately do NOT read
``X-Forwarded-For`` inside the app: trusting it unconditionally would let any
client spoof the header and get a fresh rate-limit bucket, nullifying the limit.
Behind a reverse proxy (Traefik), run uvicorn with ``--proxy-headers`` and
``--forwarded-allow-ips=<proxy subnet>`` so the socket peer already resolves to
the real client IP.

Storage is in-process per worker; switch to a shared Redis backend
(``storage_uri=settings.REDIS_URL``) when running multiple instances. Limits are
applied per-endpoint via ``@limiter.limit(...)``.
"""

from fastapi import Request
from slowapi import Limiter


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip)

# Limit on the unauthenticated/credential endpoints (login, register, refresh).
AUTH_RATE_LIMIT = "10/minute"

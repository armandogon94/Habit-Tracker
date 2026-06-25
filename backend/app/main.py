from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.ratelimit import limiter
from app.core.redis_client import close_redis
from app.routers import auth, habits


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="Habit Tracker API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting (slowapi): @limiter.limit decorators read app.state.limiter and
# raise RateLimitExceeded, which this handler renders as a 429.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


async def _redis_unavailable_handler(_request, _exc):
    # Fail closed: an auth path that can't reach Redis cannot validate sessions,
    # so return a deliberate 503 rather than a confusing 500 — and never fail open.
    return JSONResponse(status_code=503, content={"detail": "Service temporarily unavailable"})


app.add_exception_handler(RedisError, _redis_unavailable_handler)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(habits.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

# Research Findings — Best Practices Summary

> Compiled 2026-04-01 from 3 parallel research agents. Reference this when implementing features.

---

## Next.js 14+ App Router

- **Folder structure:** Feature-based with `src/` dir. Route groups `(auth)`, `(dashboard)` for organization.
- **Server vs Client components:** Server by default. Client only for `useState`, `onClick`, `useEffect`, browser APIs. Don't convert entire pages to client.
- **Data fetching:** Hybrid — RSC for initial loads (40-70% faster TTI), TanStack Query for mutations/optimistic UI/cache.
- **Auth middleware:** Defense in depth — verify in middleware AND Server Components AND Route Handlers.
- **Environment vars:** `NEXT_PUBLIC_` prefix = client-accessible. No prefix = server-only (safe for secrets).

## FastAPI Backend

- **Structure:** routers/ → services/ → repositories/ → models/. Schemas separate from models.
- **Dependency injection:** `Depends(get_db)` async generator yields session per request. Auto-commit on success, rollback on exception.
- **Alembic:** Commit migrations to git. Auto-generate for simple changes, manual for complex. Use `NullPool` for migrations.
- **Error handling:** Custom exception classes + global `@app.exception_handler()`. Consistent JSON format with message, code, timestamp.
- **Config:** Pydantic Settings — type-safe, fails fast on missing vars.

## Authentication

- **JWT tokens:** Access (15min, in memory) + Refresh (7d, httpOnly cookie). OWASP recommends cookies for security.
- **Refresh flow:** Frontend calls `/refresh` → backend reads cookie → issues new access token → frontend retries.
- **FastAPI-Users:** In maintenance mode. Better to roll your own for simple apps.
- **bcrypt:** Use directly (not via passlib — incompatible with bcrypt 5.0).

## Database Design for Habit Tracking

### Streak Calculation
- **Compute on-the-fly from habit_logs** — single source of truth, no sync issues.
- Algorithm walks backward from today counting consecutive `completed_date` values.
- If performance becomes issue: cache in Redis, or materialized view refreshed daily.

### RRULE Scheduling (RFC 5545)
- Store as text: `FREQ=DAILY`, `FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR`, etc.
- Python: `dateutil.rrule`. JavaScript: `rrule` npm package.
- PostgreSQL extension available: `postgres-rrule`.

### Timezone Handling
- `completed_date` as `DATE` (user's local date) — daily reset at user's midnight.
- All other timestamps as `TIMESTAMPTZ`.
- User's IANA timezone in `users.timezone` (e.g., `America/Los_Angeles`).

### Analytics
- Materialized views for monthly summaries (completion rate, totals).
- Refresh daily via scheduled task or pg_cron.
- Real-time streak computation for current data.

### PostgreSQL Optimizations
- Monthly RANGE partitioning on `habit_logs.log_date` (when data grows).
- Indexes: `(user_id, log_date DESC)`, `(habit_id, log_date DESC)`, `(user_id, habit_id, log_date DESC)`.
- Use `pg_partman` for automatic partition creation.

## Calendar Heatmap Visualization

- **Libraries ranked:** `@uiw/react-heat-map` (lightweight, SVG) > `react-calendar-heatmap` > `@nivo/calendar` (heavy).
- **Mobile:** Horizontal scroll (not responsive resize). Maintains day/week label readability.
- **Color:** Binary (gray/green) for yes/no. Intensity gradient rarely needed.
- **Performance:** Memoize data with `useMemo`. React.memo for large grids. Virtual scroll for 10K+ points.

## Charts & Analytics

- **Recharts** recommended (22M weekly downloads, idiomatic React API).
- Chart types for habits: Line (trends), Bar (weekly distribution), Horizontal Bar (streak comparison), Radial Gauge (completion %).
- **Performance:** `animationDuration={0}` for faster initial render. Server-side aggregation (12 months, not 365 days).

## Testing

### Backend (pytest)
- `httpx.AsyncClient` for async API tests (not sync TestClient).
- `async-factory-boy` for SQLAlchemy async fixtures.
- Function-scoped fixtures with transaction rollback for isolation.
- `pytest.ini: asyncio_mode = auto`.

### Frontend (vitest)
- 2-3x faster than Jest. Native ESM.
- `@testing-library/react` + `user-event` for interactions.
- MSW for network-level API mocking (not function mocks).
- `happy-dom` faster than `jsdom`.

### E2E (Playwright)
- Worth it for auth flow + critical paths (2-4hr setup).
- Multi-browser support (Chrome, Firefox, Safari).
- Built-in auto-waiting reduces flaky tests.

## Docker

### FastAPI Dockerfile (multi-stage)
```dockerfile
# Builder: ghcr.io/astral-sh/uv:latest → uv sync --frozen --no-dev
# Runtime: python:3.11-slim (~100MB)
# UV_LINK_MODE=copy, UV_COMPILE_BYTECODE=1
# Non-root user, .venv copied from builder
```

### Next.js Dockerfile (multi-stage)
```dockerfile
# Build: node:20-alpine → npm ci → npm run build (with output: "standalone")
# Runtime: node:20-alpine → copy .next/standalone + .next/static + public
# 75% smaller than shipping node_modules
```

### Docker Compose Dev
- Volume mounts for hot-reload on both services.
- `WATCHPACK_POLLING=true` for Next.js file watching in Docker.
- FastAPI `--reload` flag for auto-restart.

### Health Checks
- `/live` — liveness (process running).
- `/ready` — readiness (DB connected).
- Docker HEALTHCHECK with `curl -f` or `wget --spider`.

## Deployment

### Traefik
- Automatic Let's Encrypt SSL. Docker label-based routing.
- `providers.docker.exposedbydefault=false` — opt-in per service.

### Alembic in Docker
- **Dev:** Run on startup (`alembic upgrade head && uvicorn ...`).
- **Prod:** Separate migration container with `condition: service_completed_successfully`.

### CI/CD (GitHub Actions)
- Parallel jobs: lint, test-backend, test-frontend.
- Sequential: build (on test success) → deploy (on main branch push).
- Docker layer caching with `cache-from: type=gha`.

## Development Tooling

### uv
- 10-100x faster than pip. `uv sync --frozen` for CI.
- `pyproject.toml` + `uv.lock` committed to git.

### Pre-commit Hooks
- `ruff` (Python linting + formatting — replaces black + isort + flake8).
- ESLint + Prettier (TypeScript).
- `detect-private-key` for secret scanning.
- `commitizen` for conventional commit messages.

### Makefile Targets
- `dev`, `dev-db`, `dev-api`, `dev-web` — development.
- `test`, `test-api`, `test-web` — testing.
- `lint`, `format` — code quality.
- `migrate`, `migrate-create` — database.
- `build`, `deploy` — production.

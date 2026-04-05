# Habit Tracker — Persistent Memory

> Decisions, patterns, and preferences learned across Claude Code sessions.
> Last updated: 2026-04-02

---

## Project Status: MVP RUNNING LOCALLY

The full stack is implemented and verified working as of 2026-04-01.
- Backend: FastAPI on port 8020 (hot-reload via uvicorn)
- Frontend: Next.js 14 on port 3020 (hot-reload via next dev)
- Database: PostgreSQL 16 (shared instance from project 05, habits_db)
- Redis: port 6379 DB#2 (shared from project 05, not yet used in code)
- Demo user seeded: `demo@test.com` / `password123` (3 habits, 13 log entries)
- Alembic migration applied: `78e34eb83f13_initial_schema`

### To restart services:
```bash
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload &
cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8020 npm run dev -- -p 3020 &
```
Or use `make dev` (starts DB containers + both services).

---

## User Preferences

- Store ALL memory locally in `.claude/` inside project dir (NOT global `~/.claude/`)
- Uses 7 specialist roles defined in AGENTS.md — reference them when making decisions
- Prefers uv for Python, npm for Node
- No Python notebooks — all code via terminal
- Must work on Apple Silicon locally + deploy to VPS via Docker Compose + Traefik
- Domain: habits.armandointeligencia.com / api.habits.armandointeligencia.com

---

## Architectural Decisions

### [Architect] Computed Streaks Over Stored Streaks
**Decision:** Calculate streaks on-the-fly from `habit_logs` table instead of maintaining a separate `streaks` table.
**Why:** Single source of truth — no sync issues. Algorithm walks backward from today counting consecutive completed dates.
**Status:** IMPLEMENTED in `backend/app/services/streak_service.py`. Verified working — 8-day streak computed correctly.
**Trade-off:** Slightly more compute per request, but trivial for personal use. Cache in Redis (DB#2) if needed.

### [Architect] RRULE for Habit Scheduling
**Decision:** Use iCalendar RRULE format (RFC 5545) stored as text field.
**Why:** Standardized format handles all scheduling patterns. Libraries: `dateutil.rrule` (Python), `rrule` (npm).
**Status:** IMPLEMENTED — habits table has `rrule` column, default `FREQ=DAILY`. Frontend does NOT yet use RRULE for schedule-aware streak calculation or UI scheduling options.

### [Architect] Separate FastAPI Backend
**Decision:** FastAPI as independent backend, not Next.js Route Handlers.
**Status:** IMPLEMENTED — separate services on ports 8020/3020.

### [Architect] Hybrid Data Fetching
**Decision:** TanStack Query for client-side state. Server components not yet leveraged for data fetching.
**Status:** PARTIALLY IMPLEMENTED — TanStack Query works for all data. Could add RSC for initial page loads later.

---

## Database Decisions

### [DBA] Timezone Strategy
**Decision:** `completed_date` as `DATE`, timestamps as `TIMESTAMPTZ`, user timezone in `users.timezone`.
**Status:** IMPLEMENTED — models use `DateTime(timezone=True)`, users have `timezone` column.

### [DBA] Analytics via Materialized Views
**Decision:** Use materialized views instead of denormalized table.
**Status:** NOT YET IMPLEMENTED — analytics computed on-the-fly in `habit_service.py`. Materialized views can be added when performance requires it.

### [DBA] Index Strategy
**Status:** PARTIALLY IMPLEMENTED — auto-generated indexes on `habit_id` and `completed_date` columns. Composite indexes `(user_id, log_date DESC)` not yet added.

---

## Security Decisions

### [Security] Custom JWT Auth
**Decision:** Roll our own JWT (not FastAPI-Users).
**Status:** IMPLEMENTED in `backend/app/core/security.py` using `python-jose` + `bcrypt` directly.
**Note:** Had to switch from `passlib[bcrypt]` to raw `bcrypt` because passlib is incompatible with bcrypt 5.0.

### [Security] Token Storage Strategy  
**Decision:** Access token in React state, refresh token in httpOnly cookie.
**Status:** IMPLEMENTED — backend sets `refresh_token` httpOnly cookie on login/register, frontend stores access token in module-level variable (not localStorage).

### [Security] Token Lifetimes
- Access token: 15 min, Refresh token: 7 days
- Redis token whitelist: NOT YET IMPLEMENTED

---

## Frontend Decisions

### [UI/UX] Heatmap
**Decision:** Custom SVG grid heatmap (built inline in habit detail page).
**Status:** IMPLEMENTED — custom grid in `[id]/page.tsx`. Did NOT use `@uiw/react-heat-map` library (built a simpler custom version). Could upgrade later.

### [UI/UX] Charts
**Decision:** Recharts for analytics.
**Status:** IMPLEMENTED — weekly distribution BarChart in habit detail page.

### [UI/UX] Folder Structure  
**Status:** IMPLEMENTED — `src/app/` with `(auth)` and `(dashboard)` route groups, `src/components/habits/`, `src/lib/`, `src/hooks/`, `src/types/`.

---

## DevOps Decisions

### [DevOps] Package Management
- Backend: uv (pyproject.toml + uv.lock) — IMPLEMENTED
- Frontend: npm (package.json + package-lock.json) — IMPLEMENTED

### [DevOps] Docker
- docker-compose.dev.yml for PostgreSQL + Redis — CREATED (but using shared instances from project 05)
- Multi-stage Dockerfiles — NOT YET CREATED
- docker-compose.prod.yml with Traefik — NOT YET CREATED

### [DevOps] Infrastructure
- Shared PostgreSQL from project 05 container: `05-portfolio-data-platform-postgres-1`
- Password: `changeme_secure_password` (hardcoded in alembic.ini and config.py — move to .env.local)
- Shared Redis from project 05 container: `05-portfolio-data-platform-redis-1`

---

## Known Issues / Tech Debt

1. **DB password hardcoded** — `changeme_secure_password` is in `alembic.ini` and `app/core/config.py`. Should use `.env.local`.
2. **No .gitignore** — need to create one (exclude .venv, node_modules, .next, .env.local, etc.)
3. **No tests** — pytest and vitest configured but no test files written yet.
4. **No Dockerfiles** — multi-stage builds for backend and frontend not created.
5. **No docker-compose.prod.yml** — Traefik config not created.
6. **RRULE not used in streaks** — streak calculation assumes daily frequency; doesn't check RRULE schedule.
7. **Redis not connected** — configured but not used for caching or token whitelisting.
8. **No rate limiting** on auth endpoints.
9. **CORS set to localhost:3020 only** — needs updating for production.
10. **cookie secure=False** — needs to be True in production (HTTPS).
11. **No composite indexes** — `(user_id, log_date DESC)` should be added for performance.
12. **Frontend error handling** — minimal; needs better error boundaries and toast notifications.
13. **No edit habit UI** — backend supports PUT but frontend has no edit form.
14. **No CI/CD** — GitHub Actions pipeline not set up.
15. **No pre-commit hooks** — ruff/eslint/prettier not configured as git hooks.

---

## PLAN.md Schema Changes — Status

| Change | Status |
|--------|--------|
| Remove `streaks` table | DONE (never created) |
| Remove `habit_analytics` table | DONE (never created) |
| Change TIMESTAMP → TIMESTAMPTZ | DONE |
| Add `timezone` to users | DONE |
| Change `frequency` → `rrule` | DONE |
| Fix localStorage → in-memory tokens | DONE |
| Add composite indexes | TODO |

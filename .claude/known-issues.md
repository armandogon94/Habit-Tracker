# Known Issues & Tech Debt (Priority Order)

Before starting any work, check `.claude/memory.md` § Known Issues for the full priority list. High-priority items:

1. **DB password hardcoded** — `changeme_secure_password` in `alembic.ini` and `app/core/config.py`. Move to `.env.local`.
2. **RRULE not used in streaks** — RESOLVED (2026-06-24) by enforcing daily-only: the API now rejects any rrule but `FREQ=DAILY`, so the daily streak algorithm matches the contract. Real schedule-aware streaks remain deferred (see architecture-decisions.md § RRULE Scheduling, "option b").
3. **Redis not connected** — Configured but not used for caching or token whitelisting.
4. **No Dockerfiles** — Multi-stage builds for backend and frontend not created.
5. **No docker-compose.prod.yml** — Traefik config not created yet.
6. **No .gitignore** — Need to exclude .venv, node_modules, .next, .env.local, __pycache__.
7. **No tests** — STARTED (2026-06-24): first backend tests added for `streak_service` (pure streak helpers) and the rrule validator (`backend/tests/`). Still TODO: happy-path API/router tests and frontend vitest coverage.
8. **No composite database indexes** — `(user_id, completed_date DESC)` should be added for streak query performance.
9. **No edit habit UI** — Backend PUT endpoint exists, frontend form missing.
10. **No rate limiting** on auth endpoints (register, login).
11. **CORS hard-coded to localhost:3020** — Needs updating for production.
12. **Cookie secure=False** — Needs to be True in production (HTTPS only).
13. **Frontend error handling** — Minimal; needs better error boundaries and toast notifications.
14. **No CI/CD pipeline** — GitHub Actions not set up.
15. **No pre-commit hooks** — ruff/eslint/prettier not configured as git hooks.

For the full priority list with details, see `.claude/memory.md` § Known Issues / Tech Debt.

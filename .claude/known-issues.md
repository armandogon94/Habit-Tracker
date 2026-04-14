# Known Issues & Tech Debt (Priority Order)

Before starting any work, check `.claude/memory.md` § Known Issues for the full priority list. High-priority items:

1. **DB password hardcoded** — `changeme_secure_password` in `alembic.ini` and `app/core/config.py`. Move to `.env.local`.
2. **RRULE not used in streaks** — Streak calculation assumes daily frequency; doesn't check RRULE schedule. TODO: make schedule-aware.
3. **Redis not connected** — Configured but not used for caching or token whitelisting.
4. **No Dockerfiles** — Multi-stage builds for backend and frontend not created.
5. **No docker-compose.prod.yml** — Traefik config not created yet.
6. **No .gitignore** — Need to exclude .venv, node_modules, .next, .env.local, __pycache__.
7. **No tests** — pytest and vitest configured but no test files written (TODO: happy-path API tests at minimum).
8. **No composite database indexes** — `(user_id, completed_date DESC)` should be added for streak query performance.
9. **No edit habit UI** — Backend PUT endpoint exists, frontend form missing.
10. **No rate limiting** on auth endpoints (register, login).
11. **CORS hard-coded to localhost:3020** — Needs updating for production.
12. **Cookie secure=False** — Needs to be True in production (HTTPS only).
13. **Frontend error handling** — Minimal; needs better error boundaries and toast notifications.
14. **No CI/CD pipeline** — GitHub Actions not set up.
15. **No pre-commit hooks** — ruff/eslint/prettier not configured as git hooks.

For the full priority list with details, see `.claude/memory.md` § Known Issues / Tech Debt.

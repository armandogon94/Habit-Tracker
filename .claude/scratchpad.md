# Scratchpad — Session State

> Last session: 2026-04-01 → 2026-04-02

---

## What Was Done This Session

### Phase 1: Research (3 parallel agents)
1. **Next.js + FastAPI best practices** — folder structure, server vs client components, TanStack Query hybrid approach, JWT auth patterns, uv package manager
2. **Habit tracking DB + visualization** — RRULE scheduling, computed streaks, timezone handling, heatmap libraries, Recharts for analytics
3. **Testing + Docker + deployment** — pytest async patterns, vitest setup, multi-stage Dockerfiles, Traefik, GitHub Actions CI/CD

### Phase 2: Project scaffolding
- Created CLAUDE.md (project context file)
- Created README.md (GitHub documentation)
- Created .claude/memory.md (persistent decisions)
- Created .claude/scratchpad.md (this file)

### Phase 3: Full implementation
- **Infrastructure:** docker-compose.dev.yml, Makefile
- **Backend (23 files):** FastAPI app with auth, habits CRUD, streak computation, analytics, calendar heatmap data
- **Frontend (14 files):** Next.js 14 with login/register, habits list, habit detail with heatmap + Recharts chart
- **Database:** Alembic migration applied, 3 tables (users, habits, habit_logs)

### Phase 4: Verification
- Registered demo user, created 3 habits, logged 13 completions
- Verified 8-day streak computed correctly
- Both frontend (3020) and backend (8020) running with hot-reload
- Swagger docs at /docs, ReDoc at /redoc

---

## File Inventory (created this session)

### Backend (backend/)
```
pyproject.toml                          # Python deps (uv)
alembic.ini                             # Alembic config (DB URL hardcoded — fix!)
alembic/env.py                          # Async Alembic setup
alembic/script.py.mako                  # Migration template
alembic/versions/78e34eb83f13_*.py      # Initial schema migration
app/__init__.py
app/main.py                             # FastAPI app + CORS + routers
app/database.py                         # AsyncSession setup
app/core/__init__.py
app/core/config.py                      # Pydantic Settings (DB URL hardcoded — fix!)
app/core/security.py                    # JWT + bcrypt (switched from passlib)
app/core/deps.py                        # get_current_user, get_refresh_token_payload
app/models/__init__.py                  # Imports Base, User, Habit, HabitLog
app/models/base.py                      # Base, UUIDMixin, TimestampMixin
app/models/user.py                      # User model (email, password_hash, timezone)
app/models/habit.py                     # Habit model (name, color, rrule, archived_at)
app/models/habit_log.py                 # HabitLog model (habit_id, completed_date, notes)
app/schemas/__init__.py
app/schemas/auth.py                     # Register, Login, Token, User response schemas
app/schemas/habit.py                    # Habit CRUD + Calendar + Analytics schemas
app/routers/__init__.py
app/routers/auth.py                     # /api/v1/auth/* (register, login, refresh, logout, me)
app/routers/habits.py                   # /api/v1/habits/* (CRUD, log, calendar, analytics)
app/services/__init__.py
app/services/auth_service.py            # register_user, authenticate_user, get_user_by_id
app/services/habit_service.py           # All habit business logic
app/services/streak_service.py          # compute_current_streak, compute_longest_streak
```

### Frontend (frontend/)
```
package.json                            # Node deps (next 14, react 18, tanstack-query, recharts)
next.config.mjs                         # output: "standalone"
tsconfig.json                           # Strict TypeScript
tailwind.config.ts                      # TailwindCSS
postcss.config.mjs                      # PostCSS
src/app/globals.css                     # Tailwind imports + dark bg
src/app/layout.tsx                      # Root layout with Providers
src/app/page.tsx                        # Redirect to /habits or /login
src/app/(auth)/login/page.tsx           # Login form
src/app/(auth)/register/page.tsx        # Registration form
src/app/(dashboard)/habits/page.tsx     # Habits list with cards + FAB
src/app/(dashboard)/habits/[id]/page.tsx # Habit detail: stats, heatmap, weekly chart
src/components/providers.tsx            # QueryClient + AuthProvider
src/components/habits/HabitCard.tsx     # Habit card with toggle button
src/components/habits/CreateHabitModal.tsx # New habit form modal
src/hooks/useHabits.ts                  # TanStack Query hooks for all habit operations
src/lib/api.ts                          # API client with auto-refresh
src/lib/auth.tsx                        # AuthContext + useAuth hook
src/types/habit.ts                      # TypeScript interfaces
```

### Root
```
CLAUDE.md                               # Project context for Claude Code
README.md                               # GitHub README
PLAN.md                                 # Original project plan (pre-existing)
AGENTS.md                               # 7 specialist roles (pre-existing)
PORT-MAP.md                             # Port allocation (pre-existing)
.env.example                            # Env var template (pre-existing)
docker-compose.dev.yml                  # PostgreSQL + Redis (local dev)
Makefile                                # dev, test, lint, format, migrate, build, deploy
```

---

## Database State

- **PostgreSQL:** `habits_db` on shared instance (project 05 container)
- **Tables:** users, habits, habit_logs, alembic_version
- **Seed data:** 1 user, 3 habits, 13 habit_logs
- **Migration:** `78e34eb83f13_initial_schema` (current head)

---

## Bugs Fixed During Session

1. **passlib + bcrypt 5.0 incompatibility** — passlib's CryptContext raises "password cannot be longer than 72 bytes" even for short passwords. Fixed by switching to raw `bcrypt` module directly in `security.py`.

2. **Alembic module not found** — `from app.models import Base` failed because `sys.path` didn't include the backend root. Fixed by adding `sys.path.insert(0, ...)` in `alembic/env.py`.

3. **PostgreSQL port conflict** — Port 5432 already bound by project 05's container. Resolved by reusing the shared instance and creating `habits_db` in it.

---

## Next Steps (Priority Order)

1. **Create .gitignore** — exclude .venv, node_modules, .next, .env.local, __pycache__
2. **Move DB password to .env.local** — remove hardcoded password from config.py and alembic.ini
3. **Add edit habit UI** — backend PUT endpoint exists, need frontend form
4. **Add composite database indexes** — performance optimization for streak queries
5. **Write tests** — at least happy-path API tests with pytest + httpx
6. **Create Dockerfiles** — multi-stage builds for both services
7. **Create docker-compose.prod.yml** — with Traefik labels for SSL
8. **Add RRULE-aware streak calculation** — currently ignores schedule, counts all days
9. **Redis integration** — caching, token whitelisting
10. **GitHub Actions CI/CD** — lint → test → build → deploy pipeline
11. **Pre-commit hooks** — ruff, eslint, prettier
12. **Better error handling** — toast notifications, error boundaries
13. **Rate limiting** — on auth endpoints
14. **Production cookie security** — secure=True, proper SameSite, CORS origins

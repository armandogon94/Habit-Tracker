# Habit Tracker — Claude Code Context

> **Project 02** | habits.armandointeligencia.com | Next.js 14 + FastAPI + PostgreSQL

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Next.js (App Router) | 14+ |
| UI | React + TailwindCSS | 18+ |
| Data fetching | TanStack Query (React Query) | 5+ |
| Charts | Recharts | latest |
| Heatmap | @uiw/react-heat-map | latest |
| Backend | FastAPI | 0.109+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Validation | Pydantic | 2.6+ |
| Migrations | Alembic | 1.13+ |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Package mgmt | uv (Python), npm (Node) | latest |
| Deployment | Docker Compose + Traefik | v3 |

---

## Port Assignments (from PORT-MAP.md)

| Service | Host Port | Container Port |
|---------|-----------|---------------|
| Frontend (Next.js) | 3020 | 3000 |
| Backend (FastAPI) | 8020 | 8000 |
| PostgreSQL (shared) | 5432 | 5432 |
| Redis DB#2 | 6379 | 6379 |

**Database:** `habits_db` | **Redis DB:** `2` | **Domain:** `habits.armandointeligencia.com` | **API:** `api.habits.armandointeligencia.com`

---

## Directory Structure

```
02-Habit-Tracker/
├── CLAUDE.md                 # This file — project context for Claude Code
├── AGENTS.md                 # 7 specialist roles and quality checklists
├── PLAN.md                   # Original project plan (schema, API, components)
├── PORT-MAP.md               # Global port allocation across all projects
├── .env.example              # Environment variable template
├── .claude/                  # Local memory (committed to git)
│   ├── memory.md             # Persistent decisions and preferences
│   └── scratchpad.md         # Temporary working notes
├── Makefile                  # Common commands
├── docker-compose.yml        # Development stack
├── docker-compose.dev.yml    # Dev with hot-reloading
├── docker-compose.prod.yml   # Production with Traefik
│
├── backend/
│   ├── pyproject.toml        # Python deps (managed by uv)
│   ├── uv.lock               # Locked deps
│   ├── Dockerfile            # Multi-stage: uv builder → python:3.11-slim
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py           # FastAPI app entrypoint
│   │   ├── database.py       # AsyncSession setup
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic Settings
│   │   │   ├── security.py   # JWT, password hashing
│   │   │   └── exceptions.py # Custom exception handlers
│   │   ├── models/           # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── habit.py
│   │   │   └── habit_log.py
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   │   ├── user.py
│   │   │   ├── habit.py
│   │   │   └── auth.py
│   │   ├── routers/          # API endpoint groups
│   │   │   ├── auth.py
│   │   │   ├── habits.py
│   │   │   └── analytics.py
│   │   ├── services/         # Business logic
│   │   │   ├── habit_service.py
│   │   │   ├── streak_service.py
│   │   │   └── auth_service.py
│   │   └── repositories/     # Database queries (CRUD)
│   │       ├── habit_repo.py
│   │       └── user_repo.py
│   └── tests/
│       ├── conftest.py       # Async fixtures, test DB, factories
│       ├── factories.py      # async-factory-boy fixtures
│       ├── routers/
│       ├── services/
│       └── repositories/
│
├── frontend/
│   ├── package.json
│   ├── next.config.js        # output: "standalone" for Docker
│   ├── Dockerfile            # Multi-stage: node:20-alpine → standalone
│   ├── tailwind.config.ts
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx        # Root layout (providers, fonts)
│   │   │   ├── page.tsx          # Landing/redirect
│   │   │   ├── (auth)/           # Route group: login, register
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   └── (dashboard)/      # Route group: authenticated pages
│   │   │       ├── layout.tsx    # Dashboard layout (sidebar, nav)
│   │   │       ├── habits/page.tsx
│   │   │       ├── habits/[id]/page.tsx
│   │   │       └── analytics/page.tsx
│   │   ├── components/
│   │   │   ├── ui/               # Reusable primitives (Button, Modal, Card)
│   │   │   ├── habits/           # Habit-specific (HabitCard, CreateHabitModal)
│   │   │   ├── charts/           # StreakCalendar, CompletionChart
│   │   │   └── layout/           # Sidebar, Header, MobileNav
│   │   ├── lib/
│   │   │   ├── api.ts            # API client (fetch wrapper with auth)
│   │   │   ├── auth.ts           # Token management (in-memory + refresh)
│   │   │   └── utils.ts          # Date helpers, formatting
│   │   ├── hooks/
│   │   │   ├── useHabits.ts      # TanStack Query hooks for habits
│   │   │   └── useAuth.ts        # Auth state hook
│   │   └── types/
│   │       ├── habit.ts          # Habit, HabitLog, Streak types
│   │       └── api.ts            # API response types
│   └── __tests__/
│       ├── setup.ts              # vitest setup (cleanup, MSW)
│       ├── mocks/                # MSW handlers
│       └── components/
```

---

## Architectural Decisions

### Computed Streaks (not stored)
Streaks are calculated on-the-fly from `habit_logs` — no separate `streaks` table. This ensures a single source of truth. The algorithm walks backward from today counting consecutive completed dates. Cache in Redis if performance becomes an issue.

### RRULE Scheduling
Habit frequency uses iCalendar RRULE format (RFC 5545) stored as text:
- Daily: `FREQ=DAILY`
- Weekdays: `FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR`
- Custom: `FREQ=WEEKLY;BYDAY=MO,WE,FR`

Libraries: `dateutil.rrule` (Python), `rrule` (npm).

### Timezone Handling
- `completed_date` stored as `DATE` in user's local timezone
- All other timestamps use `TIMESTAMPTZ` (UTC with timezone)
- User's IANA timezone stored in `users.timezone` (e.g., `America/Los_Angeles`)
- Daily reset determined by user's midnight, not UTC midnight

### Authentication
- Custom JWT implementation (not FastAPI-Users — in maintenance mode)
- Access token: 15 min lifetime, stored in React state (memory)
- Refresh token: 7 day lifetime, stored in httpOnly cookie
- Whitelist approach: tokens tracked in Redis for immediate revocation

### Data Fetching (Hybrid)
- React Server Components for initial page loads and SEO content
- TanStack Query for client-side mutations, optimistic UI, and cache management
- No Redux — TanStack Query + React context covers all state needs

### Analytics
- Materialized views for monthly summaries (completion rate, totals)
- Refreshed daily via scheduled task
- Real-time streak computation for current data

---

## Common Commands

```bash
# Development
make dev                    # Start full stack with docker-compose.dev.yml
make dev-logs               # Tail logs from all services

# Backend (manual)
cd backend && uv sync       # Install Python dependencies
cd backend && uv run uvicorn app.main:app --port 8020 --reload

# Frontend (manual)
cd frontend && npm install   # Install Node dependencies
cd frontend && npm run dev -- -p 3020

# Database
make migrate                # Run Alembic migrations
make migrate-create MSG="add_habits_table"  # Create new migration

# Testing
make test                   # Run all tests (pytest + vitest)
make test-api               # Backend tests only
make test-frontend          # Frontend tests only

# Linting & Formatting
make lint                   # Check both Python and TypeScript
make format                 # Auto-fix formatting

# Docker
make build                  # Build production images
make deploy                 # Deploy via docker-compose.prod.yml
```

---

## Coding Conventions

### Python (Backend)
- **Formatter:** black (line-length 100)
- **Linter:** ruff (pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade)
- **Type hints** on every function signature
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **Async:** all database operations use `async/await`
- **Error handling:** custom exception classes → global handlers → consistent JSON responses

### TypeScript (Frontend)
- **Strict mode** enabled in tsconfig.json
- **Formatter:** Prettier (semi, double quotes, trailing commas)
- **Linter:** ESLint (react, react-hooks, typescript rules)
- **Components:** server components by default; add `'use client'` only when needed
- **Naming:** camelCase for functions/variables, PascalCase for components/types

### Git
- **Commits:** conventional commits format (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)
- **Pre-commit hooks:** ruff + black (Python), ESLint + Prettier (TS), detect-private-key
- **Branch naming:** `feature/`, `fix/`, `refactor/` prefixes

---

## Specialist Roles (see AGENTS.md)

Before any task, identify which roles apply:
1. **Software Architect** — system design, API contracts, module boundaries
2. **UI/UX Designer** — responsive layouts, accessibility, loading/error/empty states
3. **Test Engineer** — test strategy, coverage, fixtures, CI integration
4. **DevOps Engineer** — Docker, CI/CD, health checks, Makefile
5. **Security Engineer** — auth, input validation, CORS, rate limiting
6. **Database Administrator** — schema design, indexes, migrations, query optimization
7. **Code Reviewer** — quality, consistency, readability, type safety

Log significant decisions in `.claude/memory.md` with role context.

---

## Key Files Reference

| What | Where |
|------|-------|
| Database schema | PLAN.md lines 53-115 |
| API endpoints | PLAN.md lines 119-162 |
| SQLAlchemy models | PLAN.md lines 170-228 |
| Pydantic schemas | PLAN.md lines 233-277 |
| Streak algorithm | PLAN.md lines 287-341 |
| Docker Compose (dev) | PLAN.md lines 530-586 |
| Docker Compose (prod) | PLAN.md lines 590-657 |
| Port allocations | PORT-MAP.md |
| Environment vars | .env.example |

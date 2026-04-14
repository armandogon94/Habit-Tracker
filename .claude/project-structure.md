# Project Structure

```
02-Habit-Tracker/
├── CLAUDE.md                 # Project context for Claude Code
├── AGENTS.md                 # 7 specialist roles and quality checklists
├── PLAN.md                   # Original project plan (schema, API, components)
├── PORT-MAP.md               # Global port allocation across all projects
├── .env.example              # Environment variable template
├── .claude/                  # Local memory (committed to git)
│   ├── memory.md             # Persistent decisions and preferences
│   ├── scratchpad.md         # Temporary working notes
│   ├── research-findings.md  # Best practices from research
│   ├── project-structure.md  # Directory tree (this file)
│   ├── architecture-decisions.md
│   ├── known-issues.md
│   ├── commands.md
│   ├── coding-conventions.md
│   └── specialist-roles.md
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

## Code Organization by Layer

| Layer | Location | Purpose |
|-------|----------|---------|
| **Database Schema** | PLAN.md § DATABASE SCHEMA; `backend/alembic/versions/` | Table definitions, migrations |
| **API Endpoints** | PLAN.md § API ENDPOINTS; `backend/app/routers/` | HTTP routes and handlers |
| **SQLAlchemy Models** | PLAN.md § SQLALCHEMY MODELS; `backend/app/models/` | ORM model definitions |
| **Pydantic Schemas** | PLAN.md § PYDANTIC SCHEMAS; `backend/app/schemas/` | Request/response validation |
| **Streak Algorithm** | PLAN.md § STREAK ALGORITHM; `backend/app/services/streak_service.py` | Streak computation logic |
| **Auth Logic** | PLAN.md § AUTHENTICATION; `backend/app/core/security.py` | JWT, bcrypt, token handling |
| **Frontend Pages** | PLAN.md § FRONTEND FOLDER STRUCTURE; `frontend/src/app/` | Next.js routes and pages |
| **Frontend Components** | `frontend/src/components/` | Reusable React components |
| **Frontend Hooks** | `frontend/src/hooks/` | Custom React hooks (TanStack Query integration) |
| **Docker Dev** | PLAN.md § DOCKER COMPOSE (DEV); `docker-compose.dev.yml` | Local development stack |
| **Docker Prod** | PLAN.md § DOCKER COMPOSE (PROD); `docker-compose.prod.yml` | Production Traefik setup (NOT YET CREATED) |
| **Environment** | `.env.example` | Environment variable template |
| **Build Commands** | `Makefile` | Common development tasks |

# Habit Tracker

A full-stack habit tracking application with streak calculation, calendar heatmaps, and analytics dashboards. Built with Next.js 14, FastAPI, and PostgreSQL.

> **Live:** [habits.armandointeligencia.com](https://habits.armandointeligencia.com)

<!-- ![Habit Tracker Screenshot](docs/screenshot.png) -->

---

## Features

- **Habit Management** — Create, edit, archive, and organize daily habits with custom colors and descriptions
- **Flexible Scheduling** — Daily, weekdays-only, specific days of the week, or custom frequencies (RRULE format)
- **Streak Tracking** — Automatic current and longest streak calculation with timezone-aware daily resets
- **Calendar Heatmap** — GitHub-style contribution graph showing completion history at a glance
- **Analytics Dashboard** — Completion rates, weekly distribution charts, and trend analysis with Recharts
- **JWT Authentication** — Secure login with access tokens in memory and refresh tokens in httpOnly cookies
- **Mobile Responsive** — Touch-friendly interface with horizontal-scroll heatmaps on small screens
- **API Documentation** — Auto-generated OpenAPI/Swagger docs from FastAPI

---

## Tech Stack

**Frontend:** Next.js 14+ (App Router) | React 18 | TailwindCSS | TanStack Query | Recharts | @uiw/react-heat-map | TypeScript

**Backend:** FastAPI | SQLAlchemy 2.0 (async) | Pydantic v2 | Alembic | Python 3.11+

**Database:** PostgreSQL 16 | Redis 7

**Infrastructure:** Docker Compose | Traefik (reverse proxy + SSL) | GitHub Actions (CI/CD)

---

## Prerequisites

- [Node.js](https://nodejs.org/) 20+
- [Python](https://python.org/) 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Docker Desktop](https://docker.com/products/docker-desktop/) (for PostgreSQL, Redis, or full-stack dev)

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/armando/habit-tracker.git
cd habit-tracker

# Copy environment variables
cp .env.example .env.local

# Start everything (frontend + backend + PostgreSQL + Redis)
make dev
```

The app will be available at:
- **Frontend:** http://localhost:3020
- **Backend API:** http://localhost:8020
- **API Docs (Swagger):** http://localhost:8020/docs
- **API Docs (ReDoc):** http://localhost:8020/redoc

---

## Development Setup (Without Docker)

### Database

```bash
# Start PostgreSQL and Redis via Docker
docker run -d --name habits-postgres \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=habits_db \
  postgres:16-alpine

docker run -d --name habits-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### Backend

```bash
cd backend

# Install dependencies with uv
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the development server (with hot-reload)
uv run uvicorn app.main:app --port 8020 --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev -- -p 3020
```

---

## API Documentation

FastAPI auto-generates interactive API documentation from Pydantic schemas and route decorators:

| Format | URL | Description |
|--------|-----|-------------|
| Swagger UI | `/docs` | Interactive API explorer with try-it-out |
| ReDoc | `/redoc` | Clean, readable API reference |
| OpenAPI JSON | `/openapi.json` | Machine-readable schema for code generation |

### Key Endpoints

```
POST   /api/v1/auth/register          # Create account
POST   /api/v1/auth/login             # Get access + refresh tokens
POST   /api/v1/auth/refresh           # Refresh access token

GET    /api/v1/habits                  # List all habits
POST   /api/v1/habits                  # Create a habit
GET    /api/v1/habits/{id}             # Get habit with stats
PUT    /api/v1/habits/{id}             # Update a habit
DELETE /api/v1/habits/{id}             # Archive a habit (soft delete)

POST   /api/v1/habits/{id}/log        # Mark habit completed for a date
GET    /api/v1/habits/{id}/logs       # Get completion logs (date range)
GET    /api/v1/habits/{id}/calendar   # Get calendar heatmap data
GET    /api/v1/habits/{id}/analytics  # Get completion rate and trends
```

---

## Project Structure

```
02-Habit-Tracker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── database.py          # AsyncSession configuration
│   │   ├── core/                # Config, security, exceptions
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic validation schemas
│   │   ├── routers/             # API endpoint handlers
│   │   ├── services/            # Business logic layer
│   │   └── repositories/        # Database query layer
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # pytest + httpx AsyncClient
│   ├── pyproject.toml           # Python dependencies (uv)
│   └── Dockerfile               # Multi-stage production build
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/          # React components
│   │   ├── lib/                 # API client, auth, utilities
│   │   ├── hooks/               # Custom React hooks
│   │   └── types/               # TypeScript type definitions
│   ├── __tests__/               # vitest + React Testing Library
│   └── Dockerfile               # Multi-stage standalone build
│
├── docker-compose.yml           # Development stack
├── docker-compose.dev.yml       # Dev with hot-reloading
├── docker-compose.prod.yml      # Production with Traefik
├── Makefile                     # Common commands
└── .env.example                 # Environment variable template
```

---

## Testing

```bash
# Run all tests
make test

# Backend tests only (with coverage)
make test-api

# Frontend tests only
make test-frontend

# Watch mode (re-run on file changes)
cd backend && uv run pytest-watch
cd frontend && npm run test -- --watch
```

**Backend:** pytest with httpx AsyncClient for async API integration tests, async-factory-boy for fixtures.

**Frontend:** vitest with React Testing Library for component tests, MSW for API mocking.

**E2E:** Playwright for critical auth and habit completion flows.

---

## Deployment

The application deploys to a VPS via Docker Compose behind Traefik for automatic SSL.

```bash
# Build production images
make build

# Deploy to production
make deploy

# View production logs
make deploy-logs
```

### Production Architecture

```
Internet → Traefik (80/443)
            ├── habits.armandointeligencia.com     → Next.js (3000)
            └── api.habits.armandointeligencia.com → FastAPI (8000)
                                                      └── PostgreSQL (5432)
                                                      └── Redis (6379)
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKEND_PORT` | Host port for FastAPI | `8020` |
| `FRONTEND_PORT` | Host port for Next.js | `3020` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:password@localhost:5432/habits_db` |
| `JWT_SECRET` | Secret key for JWT signing (min 32 chars) | — |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/2` |
| `LOG_LEVEL` | Logging level | `info` |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | `http://localhost:8020` |

See [`.env.example`](.env.example) for the full template.

---

## License

MIT

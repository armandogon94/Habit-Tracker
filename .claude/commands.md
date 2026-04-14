# Common Commands

## Development

```bash
make dev                    # Start full stack with docker-compose.dev.yml
make dev-logs               # Tail logs from all services
```

## Backend (manual)

```bash
cd backend && uv sync       # Install Python dependencies
cd backend && uv run uvicorn app.main:app --port 8020 --reload
```

## Frontend (manual)

```bash
cd frontend && npm install   # Install Node dependencies
cd frontend && npm run dev -- -p 3020
```

## Database

```bash
make migrate                # Run Alembic migrations
make migrate-create MSG="add_habits_table"  # Create new migration
```

## Testing

```bash
make test                   # Run all tests (pytest + vitest)
make test-api               # Backend tests only
make test-frontend          # Frontend tests only
```

## Linting & Formatting

```bash
make lint                   # Check both Python and TypeScript
make format                 # Auto-fix formatting
```

## Docker

```bash
make build                  # Build production images
make deploy                 # Deploy via docker-compose.prod.yml
```

## Restart Services (if not using make)

```bash
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload &
cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8020 npm run dev -- -p 3020 &
```

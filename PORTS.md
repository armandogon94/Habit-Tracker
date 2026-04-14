# Port Allocation — Project 02: Habit Tracker

> All host-exposed ports are globally unique across all 16 projects so every project can run simultaneously. See `../PORT-MAP.md` for the full map.

## Current Assignments

| Service | Host Port | Container Port | File |
|---------|-----------|---------------|------|
| Frontend (Next.js) | **3020** | 3000 | docker-compose.dev.yml |
| Backend (FastAPI) | **8020** | 8000 | docker-compose.dev.yml |
| PostgreSQL | **5432** | 5432 | docker-compose.dev.yml |
| Redis | **6379** | 6379 | docker-compose.dev.yml |

## Allowed Range for New Services

If you need to add a new service to this project, pick from these ranges **only**:

| Type | Allowed Host Ports |
|------|--------------------|
| Frontend / UI | `3020 – 3029` |
| Backend / API | `8020 – 8029` |
| PostgreSQL | `5432` (already assigned — do not spin up a second instance) |
| Redis | `6379` (already assigned — do not spin up a second instance) |

## Do Not Use

Every port outside the ranges above is reserved by another project. Conflicts will prevent multiple projects from running at the same time. Always check `../PORT-MAP.md` before picking a port.

Key ranges already taken:
- `3010-3019 / 8010-8019` → Project 01
- `3030-3039 / 8030-8039` → Project 03
- `3040-3049 / 8040-8049` → Project 04
- `3050-3059 / 8050-8059` → Project 05
- `5433` → Project 03 PostgreSQL
- `5434` → Project 04 PostgreSQL
- `5435-5439` → Projects 05, 11, 12, 13, 15 PostgreSQL
- `6380-6385` → Projects 05, 10, 12, 13, 15, 16 Redis

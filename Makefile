.PHONY: help dev dev-build dev-down dev-logs dev-db dev-api dev-web test test-api test-web lint format build migrate migrate-create

SHELL := /bin/bash
ROOT := $(shell pwd)

help:
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:' Makefile | sed 's/://' | awk '{print "  " $$1}'

# ── Docker (full stack) ────────────────────────────────────────
dev:
	docker compose -f docker-compose.dev.yml up -d

dev-build:
	docker compose -f docker-compose.dev.yml up -d --build

dev-down:
	docker compose -f docker-compose.dev.yml down

dev-logs:
	docker compose -f docker-compose.dev.yml logs -f

# ── Local (without Docker, for debugging) ──────────────────────
dev-db:
	docker compose -f docker-compose.dev.yml up -d postgres redis

dev-api:
	cd $(ROOT)/backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload

dev-web:
	cd $(ROOT)/frontend && npm run dev -- -p 3020

# ── Database ───────────────────────────────────────────────────
migrate:
	docker compose -f docker-compose.dev.yml exec habits-api alembic upgrade head

migrate-create:
	cd $(ROOT)/backend && uv run alembic revision --autogenerate -m "$(MSG)"

# ── Testing ────────────────────────────────────────────────────
test: test-api test-web

test-api:
	cd $(ROOT)/backend && uv run pytest -v

test-web:
	cd $(ROOT)/frontend && npm test

# ── Linting ────────────────────────────────────────────────────
lint:
	cd $(ROOT)/backend && uv run ruff check .
	cd $(ROOT)/frontend && npx eslint src --ext .ts,.tsx

format:
	cd $(ROOT)/backend && uv run ruff check --fix . && uv run ruff format .
	cd $(ROOT)/frontend && npx prettier --write "src/**/*.{ts,tsx}"

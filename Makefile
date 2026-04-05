.PHONY: help dev dev-db dev-api dev-web dev-down test test-api test-web lint format build migrate migrate-create

SHELL := /bin/bash
ROOT := $(shell pwd)

help:
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:' Makefile | sed 's/://' | awk '{print "  " $$1}'

# Infrastructure
dev-db:
	docker compose -f docker-compose.dev.yml up -d

dev-db-down:
	docker compose -f docker-compose.dev.yml down

# Backend
dev-api:
	cd $(ROOT)/backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload

# Frontend
dev-web:
	cd $(ROOT)/frontend && npm run dev -- -p 3020

# Full stack
dev: dev-db
	@echo "Waiting for PostgreSQL..."
	@sleep 2
	@echo "Running migrations..."
	cd $(ROOT)/backend && uv run alembic upgrade head
	@echo "Starting backend and frontend..."
	@trap 'kill 0' EXIT; \
		(cd $(ROOT)/backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload) & \
		(cd $(ROOT)/frontend && npm run dev -- -p 3020) & \
		wait

# Database
migrate:
	cd $(ROOT)/backend && uv run alembic upgrade head

migrate-create:
	cd $(ROOT)/backend && uv run alembic revision --autogenerate -m "$(MSG)"

# Testing
test: test-api test-web

test-api:
	cd $(ROOT)/backend && uv run pytest -v

test-web:
	cd $(ROOT)/frontend && npm test

# Linting
lint:
	cd $(ROOT)/backend && uv run ruff check .
	cd $(ROOT)/frontend && npx eslint src --ext .ts,.tsx

format:
	cd $(ROOT)/backend && uv run ruff check --fix . && uv run ruff format .
	cd $(ROOT)/frontend && npx prettier --write "src/**/*.{ts,tsx}"

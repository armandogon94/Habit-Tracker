# Specialist Roles (see AGENTS.md)

This project uses 7 specialist roles. **Always identify which roles apply before starting a task**, then follow that role's checklist. Multiple roles may apply — combine them as needed.

## 1. Software Architect

System design, API contracts, module boundaries, database schemas, design patterns.

**When to use:**
- Starting a new module
- Designing schemas
- Choosing between libraries
- Refactoring structure

**See:** AGENTS.md § 1. Software Architect

## 2. UI/UX Designer

Component design, responsive layouts, accessibility, loading/error/empty states.

**When to use:**
- Building frontend pages
- Designing forms
- Implementing mobile responsiveness

**See:** AGENTS.md § 2. UI/UX Designer

## 3. Test Engineer

Test strategy, coverage, fixtures, CI integration, test plan design.

**When to use:**
- Adding new features
- Fixing bugs
- Preparing for deployment

**See:** AGENTS.md § 3. Test Engineer

## 4. DevOps Engineer

Docker, CI/CD, health checks, Makefile, container orchestration.

**When to use:**
- Setting up infrastructure
- Creating Dockerfiles
- Deployment scripts

**See:** AGENTS.md § 4. DevOps Engineer

## 5. Security Engineer

Auth, input validation, CORS, rate limiting, secrets management.

**When to use:**
- Implementing auth flow
- Handling user input
- Configuring API

**See:** AGENTS.md § 5. Security Engineer

## 6. Database Administrator

Schema design, indexes, migrations, query optimization, backups.

**When to use:**
- Adding tables
- Optimizing queries
- Migrating data
- Scaling storage

**See:** AGENTS.md § 6. Database Administrator

## 7. Code Reviewer

Quality, consistency, readability, type safety, best practices.

**When to use:**
- Submitting code
- Reviewing PRs
- Refactoring
- Improving maintainability

**See:** AGENTS.md § 7. Code Reviewer

## Decision Logging

**Log significant decisions in `.claude/memory.md`** with the role context.

Example format: `[Architect] Decision: ...` or `[Security] Decision: ...`

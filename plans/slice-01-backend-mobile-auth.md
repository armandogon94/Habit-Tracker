# Slice 01 — Backend mobile auth + role + rate limit + DB password to env

> **Implements:** SPEC §1 (mobile-friendly auth), §2 backend extensions, §8 backend criteria, §11 tech debt items 1, 3 (partial), 8
> **Status:** READY (depends on Slice 00 only via project state, technically parallelizable)
> **Estimated sessions:** 3–4
> **Unblocks:** Slice 02 (iOS needs `/auth/login-mobile` + `/auth/refresh-mobile` to exist)

---

## 1. Objective

Extend the existing FastAPI backend to support a native iOS client without touching the working web cookie flow. Add three things: (a) **mobile auth endpoints** that return refresh tokens in JSON (Keychain-friendly) and rotate on every refresh, with a Redis-backed whitelist for revocation; (b) a **role enum on `users`** (`user` / `admin`) with role claim in JWT for the upcoming admin slice; (c) **rate limiting** on all auth endpoints via `slowapi`. Also fix the highest-priority backend tech debt: **move the hardcoded DB password to `.env`/Pydantic Settings**. Every change is additive — no existing endpoint contract changes.

## 2. Pre-conditions

- [ ] Slice 00 done (or can be skipped if backend-only worktree)
- [ ] Redis container running (`docker ps | grep redis`); SPEC says shared from project 05
- [ ] PostgreSQL container running with `habits_db`
- [ ] `uv sync` works inside `backend/`
- [ ] User has approved adding `slowapi`, `redis`, `python-dotenv` (already present?) as deps

## 3. Files to create / modify

### Modify
- `backend/pyproject.toml` — add `slowapi`, `redis[hiredis]`
- `backend/app/core/config.py` — load DB password + redis URL from `.env`; remove hardcoded password
- `backend/app/core/security.py` — add `role` claim to JWT payload; helper `is_admin(user)`
- `backend/app/core/deps.py` — `require_admin` dependency
- `backend/app/models/user.py` — add `role: Mapped[UserRole]` (PG enum)
- `backend/app/schemas/auth.py` — add `MobileTokenResponse` (`access_token`, `refresh_token` both in body), add `MobileRefreshRequest` (refresh in body)
- `backend/app/routers/auth.py` — add `/login-mobile`, `/register-mobile`, `/refresh-mobile`, `/logout-mobile`; web endpoints unchanged
- `backend/app/services/auth_service.py` — `rotate_refresh_token`, Redis whitelist read/write
- `backend/alembic.ini` — load DB URL from env
- `backend/.env.example` (root has it; ensure backend can find it) — document new vars

### Create
- `backend/app/core/ratelimit.py` — slowapi `Limiter` instance + key func (IP + path)
- `backend/app/core/redis_client.py` — async Redis client singleton; lazy init; health check
- `backend/app/services/refresh_whitelist.py` — `add(jti, user_id, ttl)`, `is_valid(jti)`, `revoke(jti)`, `revoke_all_for_user(user_id)`
- `backend/alembic/versions/<auto>_add_user_role.py` — Alembic migration: add `role` enum + default `user`
- `backend/tests/conftest.py` — async pytest fixtures: db, client, user factory, admin factory, redis fake (`fakeredis.aioredis`)
- `backend/tests/factories.py` — async-factory-boy: `UserFactory`, `AdminUserFactory`, `HabitFactory`, `HabitLogFactory`
- `backend/tests/routers/test_auth_mobile.py` — RED tests for new endpoints
- `backend/tests/routers/test_auth_web.py` — regression tests for existing web flow (no changes)
- `backend/tests/routers/test_ratelimit.py` — login spammed past limit returns 429
- `backend/tests/services/test_refresh_whitelist.py` — whitelist behavior

### Add to root
- `backend/Makefile` targets (or root Makefile) — `make backend-test`, `make migrate`, `make migrate-create MSG=...`
- `.pre-commit-config.yaml` — ruff, black, detect-private-key (one-time, optional but recommended)

---

## 4. Tasks

### Task 1.1 — Pin deps + config to env

**Description:** Add `slowapi` + `redis[hiredis]` + `fakeredis` (test-only). Move DB password and redis URL to `.env` via Pydantic Settings. Verify existing endpoints still work.

**Acceptance:**
- [ ] `uv sync` installs new deps
- [ ] `.env` (gitignored) has `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`
- [ ] `.env.example` documents the same keys with placeholder values
- [ ] `app/core/config.py` reads them via `Settings` (Pydantic v2 `BaseSettings`)
- [ ] Hardcoded password is GONE from `config.py` AND `alembic.ini` (alembic.ini uses `${DATABASE_URL}` interpolation or `env.py` reads via `Settings`)
- [ ] Existing endpoints (`/auth/login`, `/habits/...`) still pass smoke test

**Verify:**
```bash
cd backend
grep -r "changeme_secure_password" . --exclude-dir=.venv  # must return nothing
uv run pytest tests/ -k smoke -v
```

**Files:** `pyproject.toml`, `.env`, `.env.example`, `app/core/config.py`, `alembic.ini`, `alembic/env.py`

**Skills:** `security-and-hardening` (secrets in env), `source-driven-development` (Pydantic v2 Settings docs), `database-migrations` (alembic env injection)

---

### Task 1.2 — Redis client + whitelist service + tests

**Description:** Async Redis singleton; refresh-token whitelist with TTL=7 days. RED tests using `fakeredis`.

**Acceptance:**
- [ ] `app/core/redis_client.py` exposes `async def get_redis() -> Redis` (FastAPI-injectable)
- [ ] `services/refresh_whitelist.py` — 4 functions: `add`, `is_valid`, `revoke`, `revoke_all_for_user`
- [ ] Each function is fully tested with `fakeredis.aioredis`
- [ ] Tests in RED first; then implementation; then GREEN
- [ ] Whitelist key format: `refresh:{jti}` → `{user_id}` with TTL

**Verify:** `uv run pytest tests/services/test_refresh_whitelist.py -v` GREEN.

**Files:** `app/core/redis_client.py`, `app/services/refresh_whitelist.py`, `tests/services/test_refresh_whitelist.py`, `tests/conftest.py` (fakeredis fixture)

**Skills:** `test-driven-development`, `source-driven-development` (redis-py async), `backend-patterns`

---

### Task 1.3 — User role enum + migration + JWT claim

**Description:** Add `users.role` PG enum, default `user`. Bake role into JWT access token payload. Add `require_admin` dependency.

**Acceptance:**
- [ ] Alembic migration creates enum type `user_role` (`user`, `admin`) and column with default `user`
- [ ] Existing user rows backfilled to `user` (migration handles it)
- [ ] `User.role` attribute accessible
- [ ] `create_access_token(user_id, role)` includes `"role"` in payload
- [ ] `require_admin(user = Depends(get_current_user))` raises 403 if `role != admin`
- [ ] Tests cover both roles
- [ ] One user manually promoted: `UPDATE users SET role='admin' WHERE email='demo@test.com';`

**Verify:**
```bash
uv run alembic upgrade head
uv run pytest tests/routers/test_admin_authz.py -v   # this test file is small, will be expanded slice 10
```

**Files:** `app/models/user.py`, `alembic/versions/<auto>_add_user_role.py`, `app/core/security.py`, `app/core/deps.py`, `tests/conftest.py` (admin factory), `tests/routers/test_admin_authz.py` (placeholder admin endpoint test)

**Skills:** `database-migrations`, `security-and-hardening`, `test-driven-development`

---

### Task 1.4 — Mobile auth endpoints with rotating refresh

**Description:** Add `/auth/login-mobile`, `/auth/register-mobile`, `/auth/refresh-mobile`, `/auth/logout-mobile`. Refresh tokens carry a `jti` and are whitelisted in Redis. Every refresh issues a NEW pair and invalidates the old.

**Acceptance:**
- [ ] `POST /auth/login-mobile` → 200 with `{access_token, refresh_token, expires_in, user}` — no Set-Cookie
- [ ] `POST /auth/register-mobile` → 201 same shape
- [ ] `POST /auth/refresh-mobile` body `{refresh_token: "..."}` → 200 new pair; old `jti` revoked
- [ ] Replaying the OLD refresh token returns 401
- [ ] `POST /auth/logout-mobile` body `{refresh_token: "..."}` → 200; that `jti` removed
- [ ] All web endpoints unchanged (regression test passes)
- [ ] All RED tests in `test_auth_mobile.py` GREEN

**Verify:**
```bash
uv run pytest tests/routers/test_auth_mobile.py tests/routers/test_auth_web.py -v
curl -X POST localhost:8020/api/v1/auth/login-mobile -d '{"email":"demo@test.com","password":"password123"}' -H 'Content-Type: application/json'
```

**Files:** `app/routers/auth.py` (add new endpoints; do NOT touch existing), `app/schemas/auth.py` (new schemas), `app/services/auth_service.py` (token rotation helper), `tests/routers/test_auth_mobile.py`, `tests/routers/test_auth_web.py` (regression)

**Skills:** `api-and-interface-design` (additive contract, no breaking changes), `security-and-hardening` (token rotation + whitelist), `test-driven-development`

---

### Task 1.5 — Rate limiting on auth endpoints

**Description:** `slowapi` rate limiter, 10 req/min/IP on `/auth/login`, `/auth/login-mobile`, `/auth/register`, `/auth/register-mobile`. 429 on excess.

**Acceptance:**
- [ ] `Limiter` configured in `app/core/ratelimit.py`
- [ ] Decorator applied to 4 endpoints
- [ ] Test spams 11 logins → 11th returns 429 with `Retry-After` header
- [ ] Other endpoints (e.g., `/habits`) unaffected

**Verify:** `uv run pytest tests/routers/test_ratelimit.py -v`

**Files:** `app/core/ratelimit.py`, `app/main.py` (mount limiter), `app/routers/auth.py` (add decorators), `tests/routers/test_ratelimit.py`

**Skills:** `security-and-hardening`, `source-driven-development` (slowapi docs)

---

### Task 1.6 — Pre-commit hooks (optional but recommended)

**Description:** `ruff`, `black`, `detect-private-key` as pre-commit hooks. Catches secrets and lint before commit.

**Acceptance:**
- [ ] `.pre-commit-config.yaml` at repo root
- [ ] `pre-commit install` succeeds
- [ ] Hooks run on `git commit`; fail on intentional private-key file in test fixture

**Verify:** Stage a fake `.pem`, commit fails.

**Files:** `.pre-commit-config.yaml`

**Skills:** `ci-cd-and-automation`, `security-and-hardening`

---

## 5. Test plan (RED → GREEN order)

| Test file | Cases (named exactly) | Phase |
|---|---|---|
| `test_refresh_whitelist.py` | `test_add_then_is_valid`, `test_revoke_makes_invalid`, `test_ttl_expiry`, `test_revoke_all_for_user` | 1.2 (RED first) |
| `test_admin_authz.py` (placeholder for slice 10) | `test_get_current_user_role_user_default`, `test_require_admin_rejects_user`, `test_require_admin_allows_admin` | 1.3 (RED first) |
| `test_auth_mobile.py` | `test_login_mobile_returns_pair_no_cookie`, `test_register_mobile_returns_pair`, `test_refresh_mobile_rotates_and_invalidates_old`, `test_replay_old_refresh_is_401`, `test_logout_mobile_removes_jti`, `test_login_mobile_wrong_password_is_401`, `test_register_mobile_duplicate_email_is_409` | 1.4 (RED first) |
| `test_auth_web.py` | `test_login_web_still_sets_cookie`, `test_refresh_web_still_works`, `test_register_web_unchanged` | 1.4 (regression — must stay GREEN) |
| `test_ratelimit.py` | `test_eleventh_login_returns_429`, `test_other_endpoints_not_limited` | 1.5 (RED first) |

---

## 6. Skills mapping (per task)

| Task | Primary skills | Secondary |
|---|---|---|
| 1.1 | `security-and-hardening`, `source-driven-development` | `database-migrations`, `git-workflow-and-versioning` |
| 1.2 | `test-driven-development`, `source-driven-development`, `backend-patterns` | — |
| 1.3 | `database-migrations`, `security-and-hardening`, `test-driven-development` | `api-and-interface-design` |
| 1.4 | `api-and-interface-design`, `security-and-hardening`, `test-driven-development` | `source-driven-development` (FastAPI/Pydantic v2) |
| 1.5 | `security-and-hardening`, `source-driven-development` | `test-driven-development` |
| 1.6 | `ci-cd-and-automation`, `security-and-hardening` | — |

Cross-cutting: `code-review-and-quality` end-of-slice; `verification-before-completion` per task.

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Web cookie flow regression while editing `auth.py` | High | Pin existing tests as regression suite; run on every change |
| Token rotation edge case allows session fixation | High | Whitelist check on EVERY refresh; new `jti` always; old revoked atomically |
| Redis down → all auth fails | Med | Health check at startup; fall back to "no whitelist" on dev only (env flag) |
| Alembic migration on existing data with active users | Low | Run on local DB first; backfill migration sets default explicitly; tested |
| `slowapi` config mismatched with prod IP behind Traefik | Med | Use `X-Forwarded-For` key func; document in `ratelimit.py` |
| `fakeredis` API drift from real `redis-py` | Low | Pin both versions; integration test against real Redis in slice 11 |

---

## 8. Definition of done

- [ ] All test files in §5 GREEN
- [ ] No `changeme_secure_password` anywhere outside `.env.example`
- [ ] `users.role` column exists, default `user`, one admin manually set
- [ ] `/auth/login-mobile`, `/auth/register-mobile`, `/auth/refresh-mobile`, `/auth/logout-mobile` documented in `/docs` (auto via Pydantic schemas)
- [ ] Existing `/auth/login`, `/auth/register`, `/auth/refresh`, `/auth/logout`, `/auth/me` still GREEN
- [ ] `slowapi` 429s on excess auth attempts
- [ ] Redis whitelist visible: `redis-cli -n 2 KEYS "refresh:*"` shows entries after login
- [ ] Pre-commit hooks installed (optional)
- [ ] Slice committed: `feat(backend): mobile auth, role enum, rate limiting, env config`
- [ ] User reviewed and acked → CHECKPOINT B partial (full B after slice 03)

## 9. Estimated session count

**3–4 sessions:**
- Session 1: Tasks 1.1, 1.2 (config + Redis + whitelist)
- Session 2: Task 1.3 (role + migration + JWT)
- Session 3: Task 1.4 (mobile endpoints — biggest)
- Session 4: Task 1.5 + 1.6 (rate limit + hooks + cleanup)

## 10. What unblocks the next slice

- iOS in slice 02 needs `POST /auth/login-mobile` and `POST /auth/refresh-mobile` reachable on `localhost:8020`
- `MobileTokenResponse` schema exists → iOS DTOs match exactly
- Redis whitelist invariants documented → iOS knows replay-old-refresh fails predictably
- Role claim in JWT → slice 10 admin code can rely on it

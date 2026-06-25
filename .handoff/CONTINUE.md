# CONTINUE — Habit Tracker: where we are & what's next

> Written 2026-06-25. Authoritative "what to do next" doc. To resume, just say
> **"continue with P0"** (or any item below), or name a feature directly.
> Supersedes the older `.handoff/HANDOFF.md` (that one is the pre-merge iOS
> conversion handoff — historical context only).

---

## Current state (verified, all pushed)

- **Repo:** `main` at commit `6b9f859`, pushed to `origin` =
  `github.com/armandogon94/Habit-Tracker`. Working tree clean.
- **Green:** backend **117 pytest**, frontend **7 vitest**, `ruff` clean, `tsc` clean.
- **Verify locally:**
  ```bash
  cd backend  && uv run pytest -q && uv run ruff check .
  cd frontend && npm test && npx tsc --noEmit
  ```
- **Env note:** secrets are fail-fast (no defaults). Tests inject them via
  `backend/tests/conftest.py`. To run the app locally, set `JWT_SECRET` (≥32 chars)
  and `DATABASE_URL` in `.env.local` (see `.env.example`). Redis is needed at
  runtime for auth (rotation whitelist + rate limit); tests use `fakeredis`.

### What this session already did
1. **Merged** four agents' branches + loose security fixes onto `main` (fast-forward),
   cleaned up the extra worktree/branches.
2. **3 Codex (GPT-5.5 / xhigh) review→fix cycles** — every finding fixed. Reports:
   `analysis/codex-review-cycle-1/2/3.md` + `analysis/00-EXECUTIVE-SUMMARY.md`.
3. **Slice 01 auth-hardening (core):** Redis refresh-token rotation/revocation
   (atomic `GETDEL` consume + RFC 6819 reuse detection), `/auth/*` rate limiting,
   fail-closed 503, single-flight client refresh. Report: `analysis/05-auth-hardening-review.md`.
4. **ruff** configured (FastAPI `Depends` allowed) and backend made lint-clean.

---

## Prioritized backlog

### P0 — Finish Slice 01 (auth) — `plans/slice-01-backend-mobile-auth.md`
The rotation/rate-limit core is done; remaining:
- **Mobile auth endpoints** `/auth/{login,register,refresh,logout}-mobile` returning the
  refresh token in the JSON body (Keychain-friendly), **reusing** the existing
  `refresh_whitelist.consume`/rotate service. Don't duplicate logic; keep cookie-vs-body
  in the routers only. (Task 1.4)
- **`users.role` enum** (`user`/`admin`) + Alembic migration + role claim in
  `create_access_token` + a `require_admin` dependency. (Task 1.3 — needed by the admin slice 10)
- **Deferred hardening** (all documented in `analysis/05-auth-hardening-review.md`):
  `sid`-scoped revocation (today reuse revokes ALL sessions), absolute session-expiry
  cap (`fexp`; today refresh is sliding), Redis-backed rate-limit storage (today in-process
  per worker), `Retry-After` on 429, `docker-compose.prod.yml` running uvicorn with
  `--proxy-headers --forwarded-allow-ips=<Traefik subnet>` (required for the IP rate-limit
  to work behind the proxy), user-index pruning, per-endpoint rate tuning.

### P0.5 — Integration-test harness (blocks confident backend work)
Full HTTP integration tests need a DB, but `backend/app/models/base.py` uses
Postgres-native `UUID`, so an in-memory SQLite test DB won't work. **Pick one:**
(a) add a Postgres **testcontainer** (dev dep) for `register→login→habit-CRUD→analytics`
e2e tests, or (b) switch `UUIDMixin` to dialect-agnostic `sqlalchemy.Uuid`. Codex cycle 1/2
flagged the missing router-level integration coverage; current backend tests are unit +
override-based (auth router is covered via dependency overrides + fakeredis).

### P1 — Retention features (highest ROI) — mini-specs in `analysis/03-feature-brainstorm.md`
The 3-judge panel + five-angle synthesis agree these beat the iOS-polish features. Build
thin vertical slices, TDD:
1. **Temptation Bundling Pairs** (7.0) — pair a "want" with a "should"; reframe reminders;
   track drag-along rate. Additive schema, no competitor ships it.
2. **Anchor Builder** (6.83) — implementation-intention composer ("After I ☐, I will ☐ at ☐").
3. **Never-Miss-Twice Guardrail** (6.67) — detect one miss, escalate a recovery nudge before
   the streak dies (proposed new slice-12).
4. **Grounded Weekly Reflection** (6.67, AI via Claude API), **Comeback Mode** (6.5),
   **Prestige/Graduate-a-Habit** (6.33).

### P2 — iOS app (Slice 0) — `plans/slice-00-mockup.md`
**PARKED on a decision:** the iOS scaffold (Slice 0 Task 0.1) build/test/commit awaits the
simulator-destination confirmation. Recommended: `platform=iOS Simulator,name=iPhone 17 Pro,OS=26.4`
(matches the installed Xcode 26.4 / iOS 26.4 runtime). Then:
```bash
cd ios && xcodegen generate
xcodebuild -project HabitTracker.xcodeproj -scheme HabitTracker -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.4' build test
```
commit, then Slice 0 tasks 0.2+ (theme system mirroring `04-Finance-Tracker/ios/.../Core/Theme/`,
mock data, models, `TodayView`, `DesignPlaygroundView`). **First** reconcile slice-00 against the
already-executed scaffold — the red-team flagged it as needs-work (`analysis/04`).

### P3 — Strategic decisions (these are YOURS to make)
- **The personal-tool-vs-product fork** (five-angle synthesis, `analysis/02`). Gates whether to
  build the web-admin (slice-10) and social features. Write the answer at the top of `SPEC.md`.
- **Competitive/market research never completed** — that workflow died in the first 429 burst and
  was never re-run. Re-run it (one at a time per the throttling memory) to ground the feature
  roadmap + pricing in real market data. Script: `…/workflows/scripts/habit-competitive-research-*.js`.

### P4 — Reconcile the slice plans with reality — `analysis/04`
The red-team found slices 01/03/04 were written against an *imagined* codebase. Before executing
slices 02–11, reconcile each against the real code. Also **finish the red-team** — it only
critiqued 4/14 docs before hitting the session limit (SPEC, overview, slices 02, 05–11 + synthesis
remain).

### P5 — Remaining slices (the iOS app + admin + ship)
02 iOS auth/Keychain · 03 iOS Today/Detail · 04 backend RRULE streaks (partly done — RRULE is
validated daily-only now) · 05 offline cache · 06 notifications · 07 widget · 08 Live Activity ·
09 localization · 10 web admin · 11 TestFlight. See `plans/000-OVERVIEW.md`.

---

## The reports (read these for full context)
- `analysis/00-EXECUTIVE-SUMMARY.md` — consolidated prioritized plan (start here).
- `analysis/01-adversarial-code-review.md` — 62 confirmed findings (most now fixed).
- `analysis/02-five-angle-analysis.md` — product/arch/security/UX/data + synthesis.
- `analysis/03-feature-brainstorm.md` — 30 ranked features + top-10 mini-specs.
- `analysis/04-spec-plan-redteam-partial.md` — slice-plan critique (partial).
- `analysis/05-auth-hardening-review.md` — Slice 01 fixed + deferred items.
- `analysis/codex-review-cycle-{1,2,3}.md` — the Codex hardening passes.

## Resume cues
- "continue with P0" → finish Slice 01 (mobile endpoints + role enum + deferred hardening)
- "build temptation bundling" (or any P1 feature)
- "do the iOS build" → confirms the sim destination then runs Slice 0
- "re-run the competitive research" → the never-finished market workflow
- "finish the red-team" → critique the remaining 10 plan docs

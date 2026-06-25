# SPEC: Habit Tracker — Full-Stack v2 (Web + Native iOS + Admin)

> **Status:** DRAFT — awaiting human approval before `/plan`
> **Author:** Armando Gonzalez (with Claude Code, spec-driven-development skill)
> **Date:** 2026-04-23
> **Supersedes:** PLAN.md (web-only original) for everything iOS and admin-related; PLAN.md remains the authoritative reference for web frontend layout and existing DB schema.

---

## 1. Objective

Convert the existing web-only Habit Tracker into a **three-surface product** sharing one FastAPI backend:

1. **Web client** (existing, Next.js 14) — keep working, add a role-gated **`(admin)` route group**.
2. **Native iOS 26 app** (new, SwiftUI + Swift 6) — offline-capable habit tracking with two switchable themes (Liquid Glass + Health Cards), local notifications, Home Screen widget, Live Activity for active habit timers.
3. **Backend** (existing FastAPI) — extend with mobile-friendly auth, admin endpoints, RRULE-aware streak logic, and a small set of operational hardening fixes.

### Users

| Persona | Surface | Primary need |
|---|---|---|
| Armando (primary user) | iOS daily, web occasionally | Log habits in <3 sec from anywhere, see streaks, get reminders |
| Family / friends (TestFlight) | iOS only | Same as Armando |
| Admin (also Armando, for now) | Web only | Manage users, view system metrics, manually fix bad habit logs |

### What success looks like

- iOS app launches, shows today's habits, lets me tap-to-complete in **≤2 taps from cold start with no network**.
- Theme switcher in Settings flips entire app between Liquid Glass and Health Cards live (no restart).
- Web `/admin` route is gated by `users.role = 'admin'` and shows: user list with suspend/delete, system metrics dashboard, and manual habit-log editor.
- Widget on Home Screen shows today's habits with checkable circles.
- Live Activity appears when a "timed" habit (e.g. "Meditate 10 min") starts; updates every minute; auto-completes the habit on finish.
- App is **Spanish by default** with English toggle in Settings; all user-facing strings localized.
- Personal TestFlight build installable on Armando's devices and family members'.

### Explicit non-goals (v1)

- HealthKit integration → v2
- Apple Watch app → v2
- Siri Shortcuts → v2
- iPad-optimized layouts → v2 (portrait iPhone only)
- Subscription/billing → not planned
- Social features → not planned

---

## 2. Tech Stack

### Backend (existing, extended)

| Layer | Tech | Version | Status |
|---|---|---|---|
| Language | Python | 3.11+ | existing |
| Framework | FastAPI | 0.109+ | existing |
| ORM | SQLAlchemy (async) | 2.0+ | existing |
| Migrations | Alembic | 1.13+ | existing |
| DB | PostgreSQL | 16 | existing (shared) |
| Cache / Token whitelist | Redis | 7 | configured, **NOT YET WIRED** |
| Auth (web) | JWT + httpOnly refresh cookie | — | existing |
| Auth (mobile) | JWT + Keychain refresh token (JSON) | — | **NEW** |
| Admin authz | `users.role` enum (`user`, `admin`) | — | **NEW** |

### Web (existing, extended)

| Layer | Tech | Version | Status |
|---|---|---|---|
| Framework | Next.js (App Router) | 14+ | existing |
| State / data | TanStack Query | 5+ | existing |
| Charts | Recharts | latest | existing |
| Heatmap | custom SVG | — | existing |
| `(admin)` route group | gated by role claim | — | **NEW** |

### iOS (new)

| Layer | Tech | Version |
|---|---|---|
| Project gen | XcodeGen | latest |
| Deployment target | iOS | 26.0 |
| Language | Swift | 6.0 |
| UI | SwiftUI | iOS 26 |
| Charts | Swift Charts | iOS 26 |
| Heatmap | custom Canvas + Path | — |
| Networking | URLSession + async/await | iOS 26 |
| Persistence (offline cache + write queue) | SwiftData | iOS 26 |
| Token storage | Keychain Services | iOS 26 |
| Notifications | UserNotifications | iOS 26 |
| Widget | WidgetKit | iOS 26 |
| Live Activity | ActivityKit | iOS 26 |
| Localization | `String Catalog` (`.xcstrings`) | iOS 26 |
| Themes | `AppTheme` protocol → Liquid Glass + Health Cards (mirroring 04-Finance-Tracker) | — |

---

## 3. Commands

### Backend

```bash
cd backend
uv sync                                                    # install deps
uv run uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload   # dev
uv run alembic upgrade head                                # apply migrations
uv run alembic revision --autogenerate -m "add_user_role"  # create migration
uv run pytest -v                                           # tests
uv run ruff check . && uv run ruff format .                # lint + format
```

### Web

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8020 npm run dev -- -p 3020
npm run build
npm run lint
npm test                                                   # vitest
```

### iOS

```bash
cd ios
brew install xcodegen                                      # one-time
xcodegen generate                                          # creates HabitTracker.xcodeproj
open HabitTracker.xcodeproj                                # opens Xcode
# Build / run / test from Xcode (⌘R / ⌘U) targeting iPhone 16 Pro simulator on iOS 26
```

### Project root

```bash
make dev                                                   # backend + web + DB
make test                                                  # all tests across stacks
make ios                                                   # cd ios && xcodegen && open
```

---

## 4. Project Structure

```
02-Habit-Tracker/
├── SPEC.md                  ← this file
├── PLAN.md                  ← original web plan (pre-existing reference)
├── plans/                   ← created by /plan in next phase
│   ├── 000-OVERVIEW.md
│   ├── slice-00-mockup.md
│   ├── slice-01-backend-mobile-auth.md
│   └── ...
│
├── backend/                 ← existing, extended
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py          ← extended: /refresh-mobile (JSON refresh)
│   │   │   ├── habits.py        ← extended: RRULE-aware streak
│   │   │   ├── analytics.py     ← existing
│   │   │   └── admin.py         ← NEW: /admin/users, /admin/metrics, /admin/logs
│   │   ├── services/
│   │   │   ├── streak_service.py    ← rewrite for RRULE awareness
│   │   │   └── admin_service.py     ← NEW
│   │   ├── models/
│   │   │   └── user.py              ← add `role` enum column
│   │   └── core/
│   │       ├── config.py            ← move DB password → env
│   │       ├── security.py          ← role claim in JWT
│   │       └── ratelimit.py         ← NEW: slowapi on /auth/*
│   └── tests/                       ← actually populate (currently empty)
│
├── frontend/                ← existing, extended
│   └── src/app/
│       ├── (auth)/                  ← existing
│       ├── (dashboard)/             ← existing
│       └── (admin)/                 ← NEW: role-gated route group
│           ├── layout.tsx           ← guard: redirect non-admin
│           ├── users/page.tsx
│           ├── metrics/page.tsx
│           └── logs/page.tsx
│
└── ios/                     ← NEW (mirrors 04-Finance-Tracker)
    ├── project.yml                  ← XcodeGen config
    ├── HabitTracker/
    │   ├── HabitTrackerApp.swift
    │   ├── RootView.swift
    │   ├── Core/
    │   │   ├── Theme/               ← AppTheme protocol, LiquidGlassTheme, HealthCardsTheme, ThemeStore, ThemedCard, ThemedBackdrops
    │   │   ├── Networking/          ← APIClient, APIConfig, APIError, DTO
    │   │   ├── Security/            ← KeychainTokenStore
    │   │   ├── Services/            ← AuthService, HabitsService, AnalyticsService
    │   │   ├── Persistence/         ← SwiftData stack, WriteQueue, SyncEngine
    │   │   ├── Notifications/       ← NotificationScheduler, ReminderManager
    │   │   ├── LiveActivity/        ← HabitTimerActivity (ActivityKit)
    │   │   └── MockData/            ← MockData for previews + design playground
    │   ├── Features/
    │   │   ├── Auth/                ← LoginView, RegisterView
    │   │   ├── Today/               ← TodayView (home), HabitRow, QuickLogSheet
    │   │   ├── HabitDetail/         ← StatsView, HeatmapCanvas, WeeklyChart
    │   │   ├── CreateEdit/          ← CreateHabitSheet, EditHabitSheet, RRULEPicker
    │   │   ├── Analytics/           ← AnalyticsView (Swift Charts)
    │   │   ├── Settings/            ← SettingsView, DesignPlaygroundView, LanguageToggle
    │   │   └── Onboarding/          ← FirstRunSheet (notification permission, theme pick)
    │   ├── Models/                  ← Habit, HabitLog, User domain types
    │   ├── Localization/            ← Localizable.xcstrings (es, en)
    │   └── Resources/               ← Assets.xcassets, AppIcon
    ├── HabitTrackerWidget/          ← WidgetKit extension target
    │   ├── HabitTrackerWidget.swift
    │   └── TimelineProvider.swift
    ├── HabitTrackerLiveActivity/    ← ActivityKit extension target (if separate)
    └── HabitTrackerTests/
        ├── DTOTests.swift
        ├── StreakComputationTests.swift
        ├── WriteQueueTests.swift
        └── ThemeTokenTests.swift
```

---

## 5. Code Style

### Swift (iOS)

```swift
// Protocol-based DI, async/await services, value types for DTOs.
// File header comment explains *why this file exists*, not what it does.

import SwiftUI

@Observable
@MainActor
final class TodayViewModel {
    private let habits: HabitsService
    private(set) var rows: [HabitRow] = []
    private(set) var error: APIError?

    init(habits: HabitsService) { self.habits = habits }

    func load() async {
        do { rows = try await habits.today() }
        catch let e as APIError { error = e }
        catch { error = .unknown(error.localizedDescription) }
    }

    func toggle(_ habit: Habit) async {
        // Optimistic UI: flip locally, queue write, reconcile on response.
        rows = rows.flipping(habit.id)
        await habits.queueLog(habitID: habit.id, date: .today)
    }
}
```

**Conventions:**
- Naming: PascalCase for types, camelCase for properties, `View` suffix for SwiftUI views, `Service` for service-layer types, `Store` for `@Observable` state holders.
- Concurrency: `@MainActor` on view models and UI services; mark `async` services as `actor` if shared mutable state.
- DI: pass dependencies through initializers; no global singletons except `KeychainTokenStore` and `Theme` env values.
- No third-party dependencies in v1 unless absolutely required (Swift Charts, SwiftData, WidgetKit, ActivityKit cover everything).
- One file per type; group small related helpers in a `+Extensions` file.

### Python (backend) — keep existing

- black, ruff, type hints on every signature, async DB operations, custom exceptions → global handlers.

### TypeScript (web) — keep existing

- Strict TypeScript, server components by default, ESLint + Prettier.

---

## 6. Testing Strategy

| Surface | Framework | Where | What we test | Coverage target |
|---|---|---|---|---|
| Backend | pytest + httpx + factory_boy | `backend/tests/` | Routers (happy path + auth failures), services (RRULE streak logic, admin authorization), repositories | 70%+ on services + routers |
| Web | vitest + Testing Library | `frontend/__tests__/` | Hooks (useHabits), admin guard, critical components | 50%+ on logic |
| Web E2E | Playwright (later, deferred) | `frontend/e2e/` | Login → create habit → log → see streak | smoke only |
| iOS | XCTest | `ios/HabitTrackerTests/` | DTO encode/decode, StreakComputation pure functions, WriteQueue ordering, Theme token presence | 60%+ on Core/, Models/ |
| iOS UI | SwiftUI Previews + manual sim | `Features/*/Previews` | Visual review every screen in both themes | every public screen has Preview |

**Gates:**
- Every backend slice ends with `pytest -v` green before moving on.
- Every iOS slice ends with `⌘U` green and a screenshot of each new screen in both themes.
- No skipped/disabled tests merged.

---

## 7. Boundaries

### Always do
- Run the test command listed in §3 before claiming a slice complete.
- Validate every DTO at the API boundary (Pydantic backend, Codable iOS).
- Use `KeychainTokenStore` on iOS — never `UserDefaults` for tokens.
- Localize every user-visible string via `String Catalog`; never hardcode "Login".
- Migrate DB schema via Alembic (one migration per schema change, named).
- Spec → Plan → Tasks → Implement, in that order. No skipping.
- Commit after each green slice with conventional commits (`feat:`, `fix:`, etc.).

### Ask first
- Adding any new third-party dependency (Swift Package, npm package, pip package).
- Schema changes that touch existing columns (renames, type changes, drops).
- Changing the API contract on existing endpoints (additive `/refresh-mobile` is pre-approved).
- Skipping or quarantining a test.
- Bumping the iOS deployment target below 26.0.
- Adding a feature not listed in §1 Objective.

### Never do
- Commit secrets (`.env`, `.env.local`, signing keys, `.p8`, App Store Connect API keys).
- Use `pip` directly — `uv` only (per project rule `.claude/rules/python-env.md`).
- Edit `node_modules/`, `.venv/`, `Pods/`, generated `.xcodeproj/` files.
- Disable Swift 6 strict concurrency without an ADR explaining why.
- Store the JWT access token anywhere except in-memory (web React state, iOS RAM only).
- Fix web-only tech debt items that don't help iOS until iOS v1 ships (CORS prod tightening, cookie `secure=true`, web edit-habit form, web error toasts) — they go in a backlog.

---

## 8. Success Criteria

A reviewer can verify each of these without my help:

### iOS app
- [ ] `cd ios && xcodegen && open HabitTracker.xcodeproj` opens a buildable project.
- [ ] Builds clean (no warnings) targeting iPhone 16 Pro simulator, iOS 26.
- [ ] Launches in <2 sec, lands on Today view.
- [ ] Settings → theme switcher flips between Liquid Glass and Health Cards live.
- [ ] Settings → language toggle flips Spanish ↔ English live.
- [ ] Tapping a habit row toggles completion and persists across cold restart.
- [ ] Going airplane-mode → tap habits → online → writes flush in <2 sec.
- [ ] Per-habit reminder fires at scheduled local time (verify in simulator with custom time).
- [ ] Widget shows today's habits, checkable from lock screen.
- [ ] Starting a "timed" habit shows Live Activity that ticks each minute.
- [ ] All `XCTest` targets green on `⌘U`.

### Backend
- [ ] `POST /api/v1/auth/login-mobile` returns `{ access, refresh }` JSON (no Set-Cookie).
- [ ] `POST /api/v1/auth/refresh-mobile` accepts refresh in body, returns new pair.
- [ ] `users.role` enum exists, defaults to `user`; one user manually promoted to `admin`.
- [ ] `GET /api/v1/admin/users` returns 403 for non-admin, 200 with paginated list for admin.
- [ ] `GET /api/v1/admin/metrics` returns DAU, total habits, total logs, error count last 24h.
- [ ] `PATCH /api/v1/admin/logs/{id}` allows admin to fix a wrong log entry, audited.
- [ ] Streak computation respects RRULE schedule (e.g. weekday-only habit doesn't break streak on weekend).
- [ ] `pytest -v` green; new tests cover all 4 above endpoints + RRULE streak edge cases.
- [ ] DB password loaded from `.env`, not hardcoded.
- [ ] `slowapi` rate-limits `/auth/login`, `/auth/login-mobile`, `/auth/register` to 10 req/min/IP.

### Web
- [ ] `/admin` route requires `role = admin` JWT claim, else redirects to `/habits`.
- [ ] `/admin/users`, `/admin/metrics`, `/admin/logs` pages render and use real backend data.
- [ ] Existing user flows (login/register/habits/detail) still work — no regressions.

### Mockup milestone (Slice 0 only)
- [ ] iOS app runnable in simulator with **only mock data** — zero backend dependency.
- [ ] Every main screen visible in both themes via `DesignPlaygroundView` or theme switcher.
- [ ] Screenshots committed to `ios/docs/mockup-screenshots/` for review.

---

## 9. Open Questions

> All previously open clarifying questions answered 2026-04-23 (notifications + widget + Live Activity, queued offline writes, runnable simulator mockup, admin = users + metrics + log fixes, mobile refresh endpoint OK, Spanish-first with English toggle, same API URL). Remaining items below are smaller and can be resolved during `/plan`:

1. **Live Activity scope:** Just one timer per habit, or should it support background pause/resume? → recommend simple v1: start, tick, end, no pause.
2. **Widget refresh cadence:** WidgetKit timeline budget is conservative. → recommend hourly background refresh + relevance-based.
3. **Onboarding screen on first run:** Mandatory or skippable? → recommend mandatory (notif permission + initial theme pick), one screen total.
4. **Admin metrics dashboard:** What charts? → recommend 4 cards (total users, DAU, total logs today, error count) + 1 line chart (logs/day last 30 days). Anything more is v2.
5. **Backend deployment:** Do iOS builds wait for the backend `/refresh-mobile` to be on prod, or do we point dev TestFlight at a dev backend URL? → recommend dev backend URL via `APIConfig.environment` enum.

---

## 10. Skills mapping (for `/plan` next phase)

When `/plan` runs, these skills will be invoked per slice (per CLAUDE.md routing). Documenting here so the plan author can reference:

| Slice | Primary skill | Secondary skills |
|---|---|---|
| 00 — iOS scaffold + mockup with mock data | `incremental-implementation` | `frontend-ui-engineering`, `liquid-glass-design`, `swiftui-patterns`, `ios-hig-design` |
| 01 — Backend mobile auth (`/login-mobile`, `/refresh-mobile`, role enum, rate limit) | `incremental-implementation` | `api-and-interface-design`, `security-and-hardening`, `test-driven-development`, `springboot-security`-style review (adapt to FastAPI) |
| 02 — iOS auth wired to backend (Keychain, APIClient) | `incremental-implementation` | `swift-actor-persistence`, `swift-protocol-di-testing`, `security-and-hardening` |
| 03 — iOS Today + HabitDetail wired to backend (online only) | `incremental-implementation` | `swiftui-patterns`, `source-driven-development` |
| 04 — Backend RRULE-aware streaks + composite indexes + tests | `incremental-implementation` | `test-driven-development`, `database-migrations`, `performance-optimization` |
| 05 — iOS offline cache + write queue (SwiftData) | `incremental-implementation` | `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development` |
| 06 — iOS local notifications + per-habit reminders | `incremental-implementation` | `swiftui-patterns`, `source-driven-development` |
| 07 — iOS Home Screen widget | `incremental-implementation` | `swiftui-patterns`, `frontend-ui-engineering` |
| 08 — iOS Live Activity for timed habits | `incremental-implementation` | `swiftui-patterns`, `swift-concurrency-6-2` |
| 09 — iOS Spanish + English localization | `incremental-implementation` | `swiftui-patterns` |
| 10 — Web admin route group + admin endpoints + UI | `incremental-implementation` | `frontend-ui-engineering`, `api-and-interface-design`, `security-and-hardening` |
| 11 — TestFlight prep + signing + first build | `shipping-and-launch` | `ci-cd-and-automation`, `documentation-and-adrs` |
| Cross-cutting | `code-review-and-quality` after each slice; `git-workflow-and-versioning` for every commit | — |

---

## 11. Tech debt status — what we will and won't fix

From `.claude/known-issues.md`:

| # | Item | Decision |
|---|---|---|
| 1 | DB password hardcoded | **FIX** (Slice 01) — needed by both surfaces |
| 2 | RRULE not used in streaks | **FIX** (Slice 04) — needed by iOS for correctness |
| 3 | Redis not connected | **FIX partial** (Slice 01) — wire token whitelist for mobile refresh; defer caching |
| 4 | No `docker-compose.prod.yml` | **DEFER** to Slice 11 (TestFlight prep is iOS-side; web deploy can use existing dev) |
| 5 | No tests | **FIX incrementally** — every slice adds tests for what it touches |
| 6 | No composite indexes | **FIX** (Slice 04) — needed for streak perf with growing data |
| 7 | No edit habit UI on web | **DEFER** — iOS will have it; web is admin-only soon |
| 8 | No rate limiting on auth | **FIX** (Slice 01) — needed before exposing mobile endpoints |
| 9 | CORS localhost-only | **DEFER** to Slice 11 |
| 10 | Cookie `secure=False` | **DEFER** to Slice 11 (web-only concern, no iOS impact) |
| 11 | Frontend error handling minimal | **DEFER** — admin UI gets new components anyway |
| 12 | No CI/CD | **DEFER** to Slice 11 |
| 13 | No pre-commit hooks | **NICE-TO-HAVE** any time |

---

## Approval

- [ ] Armando reviews and approves this spec.
- [ ] Once approved, run `/plan SPEC.md` to generate the slice-by-slice implementation plan.

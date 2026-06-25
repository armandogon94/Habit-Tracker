# Project Handoff

> **Written:** 2026-06-04 (second pause; folder relocation #2)
> **Project root at time of writing:** `/Users/armandogonzalez/Downloads/Claude/Deep Research Claude Code/02-Habit-Tracker`
> **Previous handoff:** This file was first written 2026-05-13 and is now rewritten end-to-end to fold in the post-move orientation done on 2026-06-04. The original is superseded by this version. The 2026-05-13 SCRATCH.md notes are still substantively accurate; SCRATCH.md is updated alongside this file.
> **Reader:** Fresh Claude Code session, zero prior memory of this work.

---

## 1. Project Overview

**Name:** Habit Tracker (Project 02 of Armando's portfolio)
**Production URL (web, not yet deployed):** `habits.armandointeligencia.com`
**Backend URL:** `api.habits.armandointeligencia.com`
**Repo state:** local only, single git repo, branch `main`, no remote.

### What it is

Originally a **web-only habit tracking app** (Next.js 14 + FastAPI + PostgreSQL). The MVP runs locally:
- Login/register, create/list/log habits, computed streaks, custom SVG heatmap, Recharts weekly chart.
- Demo user `demo@test.com` / `password123` with 3 habits and 13 logs seeded.

**Mid-conversation pivot (still in force):** convert to a **full-stack v2** with three surfaces sharing one FastAPI backend:
1. **Web** (existing Next.js, kept) + new role-gated `(admin)` route group.
2. **Native iOS 26 app** (new, SwiftUI + Swift 6) — Liquid Glass + Health Cards themes, offline cache, notifications, widget, Live Activity. Mirrors the iOS structure of sibling project `04-Finance-Tracker`.
3. **Backend** (existing FastAPI, extended) — mobile auth (Keychain refresh token), `users.role` enum, admin endpoints, RRULE-aware streaks, rate limiting, Redis token whitelist, password to env.

### Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend lang | Python | 3.11+ (existing), `.venv/python3.13` present |
| Backend framework | FastAPI | 0.109+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Migrations | Alembic | 1.13+ |
| DB | PostgreSQL | 16 (shared from project 05) |
| Cache | Redis | 7 (shared, DB#2, NOT YET WIRED) |
| Backend pkg mgr | `uv` (NEVER pip directly per `.claude/rules/python-env.md`) | latest |
| Web framework | Next.js (App Router) | 14+ |
| Web data | TanStack Query | 5+ |
| Web pkg mgr | `npm` | latest |
| iOS project gen | XcodeGen | 2.45.4 (`/opt/homebrew/bin/xcodegen`) |
| iOS deployment target | iOS | 26.0 (per `project.yml`) |
| iOS language | Swift | 6.0 |
| iOS UI | SwiftUI + Swift Charts | iOS 26 |
| iOS persistence | SwiftData | iOS 26 |
| iOS notifications | UserNotifications | iOS 26 |
| iOS widget | WidgetKit | iOS 26 |
| iOS Live Activity | ActivityKit | iOS 26 |
| Xcode (installed on this machine, 2026-06-04) | **26.4 (build 17E192)** — note: NOT Xcode 16 as the 2026-05-13 handoff assumed. `/Applications/Xcode.app/Contents/Developer` |

### Top-level directory map (current)

```
02-Habit-Tracker/
├── .handoff/                ← THIS FOLDER (handoff artifacts only)
│   ├── HANDOFF.md           ← this file
│   └── SCRATCH.md
├── .claude/                 ← project memory (committed except settings.local)
│   ├── memory.md            ← decisions across sessions
│   ├── scratchpad.md        ← session-by-session notes
│   ├── known-issues.md      ← tech debt list
│   ├── rules/python-env.md  ← uv-only rule
│   └── settings.json        ← UNTRACKED
├── .git/
├── .gitignore               ← root, web/python ignores
├── SPEC.md                  ← full-stack v2 spec (untracked; treat as approved — user proceeded to /plan)
├── PLAN.md                  ← original web-only plan (pre-existing)
├── PORT-MAP.md              ← global port allocation
├── PORTS.md                 ← project-specific ports doc
├── README.md
├── CLAUDE.md                ← project-level Claude Code context
├── AGENTS.md                ← 7 specialist roles
├── Makefile
├── docker-compose.dev.yml
├── .env.example
│
├── backend/                 ← existing FastAPI app (working)
│   ├── app/...              (main.py, database.py, core/, models/, schemas/, routers/, services/)
│   ├── alembic/             ← migration `78e34eb83f13_initial_schema` applied
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile
│   └── .venv/
│
├── frontend/                ← existing Next.js 14 app (working)
│   ├── src/app/{(auth),(dashboard)}/...
│   ├── src/components/habits/...
│   ├── src/{hooks,lib,types}/...
│   ├── package.json
│   ├── Dockerfile
│   └── node_modules/
│
├── plans/                   ← 12 slice plans + overview (untracked)
│   ├── 000-OVERVIEW.md
│   ├── slice-00-mockup.md
│   ├── slice-01-backend-mobile-auth.md
│   ├── slice-02-ios-auth-keychain.md
│   ├── slice-03-ios-today-detail-online.md
│   ├── slice-04-backend-rrule-streaks.md
│   ├── slice-05-ios-offline-cache.md
│   ├── slice-06-ios-notifications.md
│   ├── slice-07-ios-widget.md
│   ├── slice-08-ios-live-activity.md
│   ├── slice-09-ios-localization.md
│   ├── slice-10-web-admin.md
│   └── slice-11-testflight.md
│
└── ios/                     ← Slice 0 Task 0.1 partial (untracked)
    ├── .gitignore
    ├── project.yml          ← XcodeGen config
    ├── HabitTracker/
    │   ├── HabitTrackerApp.swift
    │   ├── RootView.swift
    │   └── Info.plist       ← generated by xcodegen
    ├── HabitTrackerTests/
    │   └── SmokeTest.swift
    └── HabitTracker.xcodeproj/  ← generated by xcodegen
```

---

## 2. Current Objective

**Specific task at pause:** Complete **Slice 0, Task 0.1 — XcodeGen scaffold + smoke tests** from `plans/slice-00-mockup.md`. File scaffolding and `xcodegen generate` are done; **build + tests + commit are still pending** and have been blocked across two folder moves.

**Higher-level goal:** Deliver a runnable iOS simulator mockup of Habit Tracker with both Liquid Glass and Health Cards themes, mock data only (zero backend dependency), as Slice 0 of the 12-slice full-stack v2 plan defined in `SPEC.md`.

**Definition of done for Slice 0 (mockup):**
- iOS app launches in an iPhone simulator on iOS 26.x.
- `DesignPlaygroundView` allows live theme switching between Liquid Glass and Health Cards.
- Every main screen (Today, HabitDetail, CreateHabit, Settings, Auth) renders in both themes via mock data.
- `XCTest` smoke tests green via `xcodebuild test`.
- Screenshots committed to `ios/docs/mockup-screenshots/` in both themes.

**Definition of done for the immediate task (0.1) only:**
- `cd ios && xcodegen generate` produces `HabitTracker.xcodeproj` with no warnings. ✅ DONE
- Project opens in Xcode. ⏸️ (not opened headlessly; assumed OK; verify on first run)
- App builds clean for an iPhone sim on the installed iOS 26 runtime. ⏸️
- App launches and shows the placeholder `RootView`. ⏸️
- `XCTest` target `HabitTrackerTests` runs both smoke tests green via `xcodebuild ... test`. ⏸️
- Bundle identifier `com.armandointeligencia.HabitTracker`, display name `Habit Tracker`. ✅ (encoded in `project.yml`)
- Commit with message `feat(ios): scaffold HabitTracker XcodeGen project + smoke tests`. ⏸️

---

## 3. Progress So Far

### Original work (sessions on 2026-04-23 → 2026-05-13)

1. **Project recon.** Read `.claude/memory.md`, `.claude/scratchpad.md`, `.claude/known-issues.md`. Reported back: web MVP working locally, 15 tech debt items, last meaningful work on Apr 13 (Docker setup).
2. **Pivot to v2 architecture.** User asked to convert to native iOS 26 + keep web + add admin. Cited sibling `04-Finance-Tracker` as iOS reference.
3. **Reference exploration.** Read `04-Finance-Tracker/ios/project.yml`, `Core/Theme/AppTheme.swift`, `Core/Theme/PlaceholderThemes.swift`. Captured the reference architecture (XcodeGen, iOS 26, Swift 6, `AppTheme` protocol with Liquid Glass + Health Cards, Keychain token store, `Core/Networking/Security/Services/Theme/MockData` layout).
4. **Surfaced 7 assumptions + 7 clarifying questions** to user. User answered: notifications + widget + Live Activity, queued offline writes, runnable simulator mockup, admin = users + metrics + log fixes, mobile refresh endpoint OK, Spanish-first with English toggle, same API URL.
5. **Wrote `SPEC.md`** at project root — full 11-section spec (objective, three users, success criteria, tech stack, commands, structure, code style with Swift snippet, testing strategy, boundaries, success criteria checklist, 5 remaining open questions with my recommendations, slice→skill mapping, tech debt FIX/DEFER table).
6. **Wrote `plans/000-OVERVIEW.md` + 12 slice plans** (slice-00 through slice-11). Each plan has objective, pre-conditions, files, tasks ≤5 files each, RED test plan, skills mapping, risks, DoD, session estimate, unblocks-next.
7. **Started Slice 0 Task 0.1.** Loaded `incremental-implementation` and `test-driven-development` skills. Wrote 5 files (`ios/project.yml`, `ios/HabitTracker/HabitTrackerApp.swift`, `ios/HabitTracker/RootView.swift`, `ios/HabitTrackerTests/SmokeTest.swift`, `ios/.gitignore`). Ran `xcodegen generate` from `ios/` — succeeded, created `HabitTracker.xcodeproj`.
8. **First pause (2026-05-13).** Asked user to run `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer` so `xcodebuild` would work. Session paused for folder relocation before user ran the command.

### This session (2026-06-04 post-move orientation only)

9. **Read the 2026-05-13 HANDOFF.md and SCRATCH.md in full** and confirmed every "Files Touched" path still exists at its expected location.
10. **Ran orientation pass:**
    - `git status` clean — same 5 untracked entries as before plus `.handoff/`. Branch `main`. Last 3 commits intact (`30cfaf8`, `df1989e`, `22d5e34`). No remote.
    - `xcodegen --version` → `2.45.4` (still installed).
    - `xcode-select -p` → `/Applications/Xcode.app/Contents/Developer` — **the previous sudo blocker is already resolved** (someone ran the switch between 2026-05-13 and now).
    - `xcodebuild -version` → **`Xcode 26.4 / Build 17E192`** (NOT Xcode 16 — the 2026-05-13 handoff's assumption is stale).
    - `xcrun simctl list runtimes | grep "iOS 26"` → only **iOS 26.4** runtime is installed (NOT 26.0).
    - `xcrun simctl list devices` → available iPhone sims on iOS 26.4 are: **iPhone 17 Pro, iPhone 17 Pro Max, iPhone 17e, iPhone Air, iPhone 17**. **There is no `iPhone 16 Pro` simulator** on this machine.
11. **Discovered destination-string drift.** The 2026-05-13 next-action commands use `'platform=iOS Simulator,name=iPhone 16 Pro,OS=26.0'`. That string will fail on this machine. Proposed new string `'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.4'`. Asked user to confirm before running `xcodebuild`.
12. **Did not run `xcodebuild build` or `xcodebuild test`.** Held for user confirmation on destination string + on whether to bump `XCODE_VERSION` and `IPHONEOS_DEPLOYMENT_TARGET` in `project.yml`. **No code was written, edited, or committed this session.**
13. **No `commit` made for Task 0.1.** Slice 0 Task 0.1 remains in the same in-progress state as 2026-05-13 except that the sudo blocker is now lifted and the only outstanding question is destination string + project.yml version bump.

### What's in-progress vs. done

| Item | Status |
|---|---|
| `SPEC.md` draft | ✅ written, treat as approved (user proceeded to /plan) |
| 12 slice plans + overview | ✅ written |
| Slice 0 Task 0.1 file scaffolding | ✅ done |
| Slice 0 Task 0.1 `xcodegen generate` | ✅ done |
| `xcode-select` pointing at Xcode.app | ✅ done (resolved between 2026-05-13 and 2026-06-04) |
| Destination string updated for installed sims | ⏸️ pending user confirm (proposal: `iPhone 17 Pro`, `OS=26.4`) |
| Slice 0 Task 0.1 `xcodebuild` build verify | ⏸️ blocked on destination decision |
| Slice 0 Task 0.1 `xcodebuild` test verify | ⏸️ blocked on destination decision |
| Slice 0 Task 0.1 commit | ⏸️ not done |
| Slice 0 Tasks 0.2 – 0.N (theme system, mock data, screens, design playground) | ⏸️ not started |
| Tech debt fixes (per `SPEC.md` §11) | ⏸️ deferred to slices 01 & 04 |

---

## 4. Files Touched

### Created in earlier sessions (carried forward; UNCHANGED this session)

| Path | Purpose |
|---|---|
| `SPEC.md` | Full-stack v2 spec for web + iOS + admin. Authoritative going forward; supersedes web parts of `PLAN.md`. |
| `plans/000-OVERVIEW.md` | Master index of the 12 slices with dependency graph and skill table. |
| `plans/slice-00-mockup.md` | iOS scaffold + 2 themes + design playground + mock data. |
| `plans/slice-01-backend-mobile-auth.md` | `/auth/login-mobile`, `/auth/refresh-mobile`, `users.role` enum, rate limiting, password→env, partial Redis. |
| `plans/slice-02-ios-auth-keychain.md` | iOS Keychain token store + APIClient + AuthService. |
| `plans/slice-03-ios-today-detail-online.md` | iOS Today + HabitDetail wired to backend (online only). |
| `plans/slice-04-backend-rrule-streaks.md` | RRULE-aware streak service + composite indexes + tests. |
| `plans/slice-05-ios-offline-cache.md` | SwiftData cache + write queue + sync engine. |
| `plans/slice-06-ios-notifications.md` | Per-habit local reminders via UserNotifications. |
| `plans/slice-07-ios-widget.md` | Home Screen widget (WidgetKit) showing today's habits. |
| `plans/slice-08-ios-live-activity.md` | Live Activity for timed habits via ActivityKit. |
| `plans/slice-09-ios-localization.md` | Spanish (default) + English toggle via String Catalog. |
| `plans/slice-10-web-admin.md` | Web `(admin)` route group + `/admin/users`, `/admin/metrics`, `/admin/logs`. |
| `plans/slice-11-testflight.md` | Signing, App Store Connect, TestFlight build, ADR. |
| `ios/project.yml` | XcodeGen config: HabitTracker app target + HabitTrackerTests unit-test bundle, iOS 26.0, Swift 6.0, bundle id `com.armandointeligencia.HabitTracker`, display name "Habit Tracker", portrait-only iPhone, `NSAllowsLocalNetworking=true`. **NOTE:** `XCODE_VERSION: "16.0"` field is in this file; with Xcode 26.4 installed, consider bumping or removing the constraint (see §8). |
| `ios/HabitTracker/HabitTrackerApp.swift` | `@main` SwiftUI App entry, hosts `RootView()` in `WindowGroup`. |
| `ios/HabitTracker/RootView.swift` | Placeholder view with checkmark icon, "Habit Tracker" title, slice/task label. Has `#Preview`. |
| `ios/HabitTrackerTests/SmokeTest.swift` | Two XCTest cases: `testAppEntryPointExists` (refs `HabitTrackerApp.self`), `testRootViewInstantiates` (refs `RootView()`). Forces test target to link app module. |
| `ios/.gitignore` | iOS-specific ignores: `xcuserdata/`, `build/`, `DerivedData/`, `.build/`, `.swiftpm/`, `Package.resolved`, `Pods/`, fastlane outputs, `.DS_Store`. |

### Generated (by xcodegen, regenerable; UNCHANGED this session)

| Path | Notes |
|---|---|
| `ios/HabitTracker.xcodeproj/` | Generated from `project.yml`. Regenerate any time with `cd ios && xcodegen generate`. |
| `ios/HabitTracker/Info.plist` | Generated alongside the xcodeproj. |

### Created this session (2026-06-04)

| Path | Purpose |
|---|---|
| `.handoff/HANDOFF.md` | This file (rewritten end-to-end). |
| `.handoff/SCRATCH.md` | Side-notes file (rewritten end-to-end). |

### Edited / Deleted / Moved this session

**None.** Per user instruction "Do NOT modify any existing project files", no project files were touched; only `.handoff/` was rewritten.

---

## 5. Key Decisions & Rationale

### Architecture-level (locked in `SPEC.md`)

| Decision | Rationale | Alternatives rejected |
|---|---|---|
| **One FastAPI backend, three surfaces** | Reuse existing investment, share auth + DB, simpler ops. | Separate Vapor/NestJS backend for iOS (rewrite cost, divergence risk). |
| **Web admin = role-gated route group, not separate service** | Cheaper, shares auth + DB. Admin = Armando only for now. | Separate Next.js admin app (overengineered). |
| **iOS bundle path:** `02-Habit-Tracker/ios/HabitTracker/` | Mirrors `04-Finance-Tracker/ios/FinanceTracker/`. Familiar. | `02-Habit-Tracker/HabitTrackerIOS/` (differs from sibling). |
| **XcodeGen + Swift 6 + iOS 26** | Identical to sibling 04. Project file regeneratable, no merge conflicts. | Tuist (unfamiliar); raw Xcode (merge hell). |
| **Themes:** Liquid Glass + Health Cards via `AppTheme` protocol with `ThemeStore` | Direct copy of sibling 04's pattern, proven. Two themes only. | Single theme (boring); 5 themes (overhead). |
| **Mobile auth:** Keychain refresh token + JSON `/refresh-mobile` endpoint | httpOnly cookie pattern doesn't translate to native iOS. Keychain is iOS standard. | Reuse cookie via WKWebView (hack); never refresh (poor UX). |
| **Offline:** read cache + queued writes via SwiftData | Habit logging must work on plane/subway. Last-writer-wins on sync. | Online-only (rejected); CloudKit (overkill v1). |
| **Mockup deliverable:** runnable simulator with mock data + theme switcher | User picked option (b). Visual contract before API code. | Figma/screenshots (no interaction); Previews only (no nav). |
| **Localization:** Spanish first, English toggle in Settings via String Catalog (`.xcstrings`) | LATAM audience same as portfolio sibling projects. | English only (wrong audience); auto-detect only (no override). |
| **Notifications + Widget + Live Activity in v1** | User answer "A". HealthKit, Watch, Siri Shortcuts deferred to v2. | All Apple frameworks now (too much surface). |

### Tech debt triage (per `SPEC.md` §11)

**FIX during slices:**
- DB password hardcoded → Slice 01 (env var)
- RRULE not used in streaks → Slice 04 (correctness)
- Redis partial wire (token whitelist only) → Slice 01
- Composite indexes `(user_id, completed_date DESC)` → Slice 04
- Rate limiting on `/auth/*` → Slice 01

**DEFER until iOS v1 ships:**
- `docker-compose.prod.yml` → Slice 11
- CORS prod tightening → Slice 11
- Cookie `secure=True` → Slice 11 (web-only)
- Web edit habit form → defer (iOS will have it; web becomes admin-only)
- Frontend toasts/error boundaries → defer
- CI/CD → Slice 11

### Open `SPEC.md` questions resolved by my recommendations during `/plan`

1. **Live Activity scope:** simple v1: start, tick, end, no pause.
2. **Widget refresh cadence:** hourly background refresh + relevance-based.
3. **Onboarding:** mandatory, one screen total (notif permission + initial theme pick).
4. **Admin metrics dashboard:** 4 cards (total users, DAU, total logs today, error count last 24h) + 1 line chart (logs/day last 30 days).
5. **Backend env for TestFlight builds:** dev backend URL via `APIConfig.environment` enum (`dev` / `staging` / `prod`).

### Decisions PENDING from this session (no defaults applied yet)

- **iOS sim destination string.** Currently invalid for this machine. My proposal: `'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.4'`. Alternatives: (a) install iOS 26.0 + iPhone 16 Pro sim to match the original spec; (b) use a different iPhone 17 variant. **No code/config changed in this session.**
- **`project.yml` version bump.** Currently pins `XCODE_VERSION: "16.0"`. With Xcode 26.4 installed it likely needs `"26.0"` or removal of the constraint. Same for any tooling version checks. **Not changed.**
- **`IPHONEOS_DEPLOYMENT_TARGET`.** Currently `"26.0"`. Xcode 26.4 SDK targets iOS 26.4 by default but apps still deploy to 26.0 just fine. Leave as 26.0 unless a Slice 06+/widget API forces 26.x bump. **Not changed.**

---

## 6. Conventions & Patterns

### Swift / iOS

- **Naming:** PascalCase types, camelCase properties, `View` suffix for SwiftUI views, `Service` suffix for service-layer types, `Store` suffix for `@Observable` state holders.
- **Concurrency:** `@MainActor` on view models and UI services. Use `actor` for shared mutable state. Swift 6 strict concurrency on (do NOT disable without an ADR).
- **DI:** Pass dependencies through initializers. No global singletons except `KeychainTokenStore` and the `Theme` environment value.
- **No third-party deps in v1** unless absolutely required. Swift Charts, SwiftData, WidgetKit, ActivityKit, UserNotifications cover everything.
- **One file per type.** Group small related helpers in a `+Extensions` file.
- **File header comment** explains *why this file exists*, not what it does (mirroring sibling 04 pattern).
- **Tokens through theme:** never hardcode colors/fonts/spacing — read from `theme.background`, `theme.font.body`, `theme.spacing.lg`, `theme.radii.card`.

### Python (backend) — preserve existing conventions

- `black` (line-length 100), `ruff` (pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade).
- Type hints on every function signature.
- All DB ops `async/await`.
- Custom exception classes → global handlers → consistent JSON responses.

### TypeScript (web) — preserve existing conventions

- Strict mode in `tsconfig.json`, Prettier (semi, double quotes, trailing commas), ESLint (react, react-hooks, typescript).
- Server components by default; `'use client'` only when needed.

### Git

- **Conventional commits:** `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- **Scope when meaningful:** `feat(ios):`, `feat(backend):`, `feat(web):`.
- **NO `Co-Authored-By` trailers.** Per global `~/.claude/CLAUDE.md`: only Armando Gonzalez `<armandogon94@gmail.com>` should appear as author/contributor.
- **Atomic commits.** One logical thing per commit. Each commit must leave the codebase compilable + tests green.
- **No `--no-verify`, no `--no-gpg-sign`.** Pre-commit hooks must pass.

### Testing

- **TDD where it makes sense:** RED test before implementation for behavior code (services, view models, write queue, streak logic).
- **Backend:** `pytest -v` with httpx + factory_boy. 70%+ coverage on services + routers.
- **Web:** vitest + Testing Library. 50%+ on logic.
- **iOS:** XCTest in `HabitTrackerTests/`. 60%+ on `Core/` and `Models/`. Every public screen has a `#Preview`. Manual screenshot of every new screen in both themes per slice.
- **No skipped/disabled tests** without an ADR.

### Workflow (per global `~/.claude/CLAUDE.md`)

`/spec` → `/plan` → `/build` → `/test` → `/review` → `/ship`. Skills auto-invoked per phase. Each `/build` slice ends with green tests + commit + tell user the next command.

---

## 7. Environment & Setup

### Required tools (status as of 2026-06-04)

```bash
xcodegen --version          # 2.45.4    ✅
xcode-select -p             # /Applications/Xcode.app/Contents/Developer    ✅ (was CLT in 2026-05-13)
xcodebuild -version         # Xcode 26.4 / Build 17E192    ✅ (NOT Xcode 16)
xcrun simctl list runtimes | grep "iOS 26"   # iOS 26.4 - 23E244   ⚠️ no iOS 26.0
xcrun simctl list devices   # iPhone 17 Pro / 17 Pro Max / 17e / 17 / Air available; NO iPhone 16 Pro
uv --version                # used by backend (verified existing project)
node --version              # used by frontend
psql --version              # 16 (shared instance from project 05)
redis-cli ping              # shared instance from project 05
```

### One-time setup commands required to unblock build

**Sudo step no longer needed** (already done). If the box ever reverts to CLT, re-run:
```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
xcodebuild -version          # confirm Xcode 26.x
```

### Required services (running, names only)

| Service | Container name | Notes |
|---|---|---|
| PostgreSQL 16 | `05-portfolio-data-platform-postgres-1` (shared from project 05) | Database `habits_db` already exists |
| Redis 7 | `05-portfolio-data-platform-redis-1` (shared from project 05) | DB#2; not yet wired in code |

### Required env vars (NAMES ONLY — values stored in `.env.local`, never in repo)

```
DATABASE_URL                    # currently HARDCODED in alembic.ini and config.py — Slice 01 fixes
JWT_SECRET_KEY                  # ditto
ACCESS_TOKEN_EXPIRE_MINUTES     # default 15
REFRESH_TOKEN_EXPIRE_DAYS       # default 7
REDIS_URL                       # for token whitelist (Slice 01)
NEXT_PUBLIC_API_URL             # web frontend → backend URL
APPLE_TEAM_ID                   # Slice 11 only
APP_STORE_CONNECT_API_KEY_ID    # Slice 11 only
APP_STORE_CONNECT_API_KEY_PATH  # Slice 11 only (.p8 file)
```

### How to install / run / build / test

#### Backend
```bash
cd backend
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload
uv run alembic upgrade head
uv run pytest -v
uv run ruff check . && uv run ruff format .
```

#### Web
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8020 npm run dev -- -p 3020
npm run build
npm run lint
npm test
```

#### iOS (commands valid AFTER user confirms destination string)
```bash
cd ios
xcodegen generate                              # regenerates HabitTracker.xcodeproj

# UPDATED destination (pending user confirm). Original 2026-05-13 string was
# 'platform=iOS Simulator,name=iPhone 16 Pro,OS=26.0' but neither iPhone 16 Pro
# nor iOS 26.0 are installed on this machine. Proposal:
DEST='platform=iOS Simulator,name=iPhone 17 Pro,OS=26.4'

xcodebuild -project HabitTracker.xcodeproj -scheme HabitTracker -destination "$DEST" build
xcodebuild -project HabitTracker.xcodeproj -scheme HabitTracker -destination "$DEST" test
```

#### Project root
```bash
make dev           # backend + web + DB
make test          # all stacks
make migrate       # Alembic up
```

### Project rules to respect

- **`.claude/rules/python-env.md`:** ALWAYS use `uv` for Python. NEVER `pip`, `conda`, `virtualenv`, or `python -m venv`.
- **NEVER commit secrets.** `.env`, `.env.local`, `.p8` files, App Store Connect keys, signing certificates.
- **NEVER edit `node_modules/`, `.venv/`, `Pods/`, generated `.xcodeproj/` files** (apart from intentional `xcodegen`-driven regen).
- **NEVER add `Co-Authored-By` trailers** to commits.
- **iOS deployment target stays at 26.0.** Lowering requires an ADR.
- **Swift 6 strict concurrency stays on.** Disabling requires an ADR.
- **JWT access token NEVER stored in `UserDefaults` or persistent storage** — RAM only on iOS, React state only on web.

---

## 8. Open Questions & Blockers

### Hard blockers (must resolve before next code action)

1. **Destination string mismatch.** The 2026-05-13 next-action commands say `name=iPhone 16 Pro,OS=26.0`. On this machine those don't exist. Need user OK on:
   - Switch to `name=iPhone 17 Pro,OS=26.4` (cheap, recommended), OR
   - Install iOS 26.0 platform + iPhone 16 Pro device in Xcode (slow, large download), OR
   - Pick a different iPhone 17 variant.
2. **`project.yml` Xcode version constraint.** Field `XCODE_VERSION: "16.0"` is stale. Either bump to `"26.0"` or remove. May or may not block the actual build — xcodebuild itself doesn't enforce `XCODE_VERSION`; that key is informational in xcodegen. Worth verifying after first build attempt.

### Soft blockers / pending decisions

- **`SPEC.md` formal approval.** User never typed "approve spec" verbatim but proceeded to `/plan`, which functionally approves it. Treat as approved unless user says otherwise.
- **Apple Developer Team ID.** `project.yml` has `DEVELOPMENT_TEAM: ""`. Slice 11 (TestFlight) needs the real Team ID. For Slice 0 sim build, an empty team is fine.
- **Mobile API URL during dev.** Slice 02 will need an `APIConfig.environment` enum with cases `dev` (`http://localhost:8020`), `staging`, `prod` (`https://api.habits.armandointeligencia.com`). Default to `.dev` for sim builds.
- **Whether to bump `IPHONEOS_DEPLOYMENT_TARGET` from 26.0 to 26.4.** Recommend NO — deploying to the lower runtime version keeps the user base wider.

### Known issues (not blockers, scheduled in slices)

See `SPEC.md` §11 and `.claude/known-issues.md` for the full list of 15 tech debt items with FIX/DEFER decisions.

### Failing tests / broken state

- None. Slice 0 Task 0.1 has not been built or tested yet, so there are no failing tests. The smoke tests should succeed when the build runs (they only verify type existence).
- Existing backend `pytest` suite is empty (zero tests written). Web `vitest` suite is empty. Pre-existing state.

---

## 9. Next Steps

### The exact next action (paste-ready for fresh Claude)

> **You are resuming Slice 0 Task 0.1 of the Habit Tracker iOS conversion.** Read `.handoff/HANDOFF.md` end-to-end first. The project just moved folders again — note the new project root.
>
> 1. Confirm Xcode wiring (the sudo step from the 2026-05-13 handoff is already done; verify):
>    ```bash
>    xcode-select -p            # expect /Applications/Xcode.app/Contents/Developer
>    xcodebuild -version        # expect Xcode 26.x (currently 26.4)
>    xcrun simctl list devices  # confirm an iPhone 17 series device on iOS 26.4
>    ```
> 2. Ask user to confirm the destination string. **Default proposal:** `'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.4'`. Wait for confirmation. Do NOT auto-pick.
> 3. Once confirmed, run from `<NEW_PROJECT_ROOT>/ios`:
>    ```bash
>    xcodegen generate
>    DEST='platform=iOS Simulator,name=iPhone 17 Pro,OS=26.4'   # or whatever user confirmed
>    xcodebuild -project HabitTracker.xcodeproj -scheme HabitTracker -destination "$DEST" build
>    xcodebuild -project HabitTracker.xcodeproj -scheme HabitTracker -destination "$DEST" test
>    ```
> 4. If build + tests green: stage `ios/`, `SPEC.md`, `plans/`, commit with exactly:
>    ```
>    feat(ios): scaffold HabitTracker XcodeGen project + smoke tests
>
>    Slice 0 Task 0.1. iOS 26 / Swift 6 SwiftUI app generated via XcodeGen,
>    mirroring sibling 04-Finance-Tracker layout. Two passing XCTest smoke
>    tests verify the test target links the app module.
>    ```
>    NO `Co-Authored-By` trailer.
> 5. Mark Task 0.1 done in `plans/slice-00-mockup.md`. Report status to user. Propose Task 0.2 with the next command.

### Next 4 actions in order (after Task 0.1 commit)

1. **Slice 0 Task 0.2 — Theme system foundation.** Create `ios/HabitTracker/Core/Theme/AppTheme.swift` (protocol + token types), `LiquidGlassTheme.swift`, `HealthCardsTheme.swift`, `ThemeStore.swift` (`@Observable`, `@MainActor`), `ThemedCard.swift`, `ThemedBackdrops.swift`. Mirror sibling `04-Finance-Tracker/ios/FinanceTracker/Core/Theme/` directly. Add 1 XCTest `ThemeTokenTests` that asserts both themes provide non-nil values for every protocol member.
2. **Slice 0 Task 0.3 — MockData.** Create `ios/HabitTracker/Core/MockData/MockData.swift` with realistic Habit + HabitLog samples (e.g., "Meditate 10m" daily, "Read" weekday-only, "Exercise" MWF). Static factory methods.
3. **Slice 0 Task 0.4 — Models.** Create `ios/HabitTracker/Models/Habit.swift`, `HabitLog.swift`, `User.swift` as Swift value types (Codable, Hashable, Identifiable). DTO types live separately (`Core/Networking/DTO.swift`, future slice).
4. **Slice 0 Task 0.5 — TodayView with mock data.** Create `ios/HabitTracker/Features/Today/TodayView.swift` reading from MockData, themed via environment. Replace `RootView`'s placeholder with `TodayView()`. Add `#Preview` showing both themes side-by-side via `Group`.

Continue through `plans/slice-00-mockup.md` until `DesignPlaygroundView` lands.

### Watch out for

- **All absolute paths in this handoff become stale on a folder move.** Treat them as patterns; recompute from the new project root.
- **`.gitignore` at root excludes `__pycache__`, `node_modules`, `.next`, `.venv`** — `ios/.gitignore` only covers iOS-specific. The new project root should still have both.
- **`HabitTracker.xcodeproj/` is generated.** Don't manually edit. Always regenerate via `xcodegen generate`. The `.gitignore` excludes `xcuserdata/` but NOT `project.pbxproj` — that file IS committed (sibling 04 commits it; mirror that choice).
- **Sim destination string is exact** and is the most common source of `xcodebuild` errors. Always re-confirm devices with `xcrun simctl list devices` on a fresh machine before committing the build command.
- **Don't use the SwiftUI `@Observable` macro inside an `actor`.** `@Observable` requires `@MainActor` for safety. Services that need actor isolation should be separate from view-state stores.
- **Sibling `04-Finance-Tracker` is the visual + structural reference.** When in doubt, copy its file shape literally and rename `Finance` → `Habit`. **Only READ that project — never write to it.**
- **Xcode 26.4 vs. project.yml `XCODE_VERSION: "16.0"` mismatch.** If `xcodegen` warns or the build fails citing the version, bump that field to `"26.0"` (or remove it entirely).
- **The previous session summary at the top of any new session may name a different project (e.g., `17-Instagram-Slides`).** That's noise from concurrent Claude sessions. Trust this handoff for the `02-Habit-Tracker` project state.

---

## 10. External References

### Sibling reference project (read-only inspiration)

```
<workspace_root>/04-Finance-Tracker/
├── ios/
│   ├── project.yml                                  ← XcodeGen template we mirrored
│   └── FinanceTracker/
│       ├── Core/Theme/AppTheme.swift                ← protocol shape to copy
│       ├── Core/Theme/PlaceholderThemes.swift       ← HealthCardsTheme reference
│       ├── Core/Theme/ThemeStore.swift              ← state management pattern
│       ├── Core/Theme/ThemedCard.swift              ← reusable card wrapper
│       ├── Core/Theme/ThemedBackdrops.swift         ← background gradients
│       ├── Core/Networking/{APIClient,APIConfig,APIError,DTO}.swift
│       ├── Core/Security/KeychainTokenStore.swift
│       ├── Core/Services/{AuthService,ExpensesService,CategoriesService}.swift
│       ├── Core/MockData/MockData.swift
│       └── Features/Settings/DesignPlaygroundView.swift   ← theme A/B view
```

> **Update path before consulting** — absolute path is no longer pinned; resolve under the current Claude workspace root.

### Documentation / framework references

- Apple SwiftUI iOS 26: https://developer.apple.com/documentation/swiftui
- Swift Charts: https://developer.apple.com/documentation/charts
- SwiftData: https://developer.apple.com/documentation/swiftdata
- WidgetKit: https://developer.apple.com/documentation/widgetkit
- ActivityKit (Live Activities): https://developer.apple.com/documentation/activitykit
- String Catalogs (`.xcstrings`): https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog
- XcodeGen: https://github.com/yonaskolb/XcodeGen
- iCalendar RRULE (RFC 5545): https://datatracker.ietf.org/doc/html/rfc5545#section-3.3.10
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0 async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- slowapi (FastAPI rate limiting): https://github.com/laurentS/slowapi
- TanStack Query v5: https://tanstack.com/query/v5

### Skills referenced (per CLAUDE.md `/spec`, `/plan`, `/build` mappings)

`spec-driven-development`, `planning-and-task-breakdown`, `incremental-implementation`, `test-driven-development`, `swiftui-patterns`, `swift-actor-persistence`, `swift-protocol-di-testing`, `swift-concurrency-6-2`, `liquid-glass-design`, `ios-hig-design`, `frontend-ui-engineering`, `api-and-interface-design`, `security-and-hardening`, `database-migrations`, `performance-optimization`, `source-driven-development`, `code-review-and-quality`, `git-workflow-and-versioning`, `shipping-and-launch`, `ci-cd-and-automation`, `documentation-and-adrs`.

### Library versions to lock when present (deferred; not committed yet)

- XcodeGen 2.45.4 (already installed)
- No Swift Package dependencies in v1 by design.

---

## 11. Git State

### At time of this handoff (2026-06-04)

```
Branch: main
Last 3 commits:
  30cfaf8 Add PORTS documentation and update CLAUDE.md configuration
  df1989e feat: dockerize frontend and backend services
  22d5e34 Initial commit

Untracked (`git status --short`):
  ?? .claude/rules/
  ?? .claude/settings.json
  ?? .handoff/
  ?? SPEC.md
  ?? ios/
  ?? plans/

No remote configured.
Working tree: clean apart from the untracked entries above.
```

### Recommendation before folder move

**Option A (preferred): commit nothing, move folder, commit fresh in new location.**
The folder move doesn't affect git internals (`.git/` moves with the folder). After move, `git status` will show the same untracked files. Make the Slice 0 Task 0.1 commit in the new location once `xcodebuild build` and `xcodebuild test` both succeed.

**Option B: commit untracked work-in-progress now under a WIP commit.**
Risk: an unverified commit (no build proof). Only do this if you fear losing files in transit.

**Option C: stash.** Doesn't apply — `stash` only covers tracked changes. Untracked files would need `git stash --include-untracked` which is bulkier than just moving the folder.

### After move

1. Verify `git status` shows the same 6 untracked entries (`.claude/rules/`, `.claude/settings.json`, `.handoff/`, `SPEC.md`, `ios/`, `plans/`).
2. Verify `git log --oneline -3` still shows the same three commits.
3. Verify `git remote -v` (still local-only, no remote).
4. Proceed with Slice 0 Task 0.1 verification + commit per §9.

---

## 12. Anything Else

### Session-metadata noise

The session-start system reminder in the current session named a different concurrent project (`17-Instagram-Slides`). That's noise from a parallel Claude Code session. **Ignore it.** This handoff is the source of truth for `02-Habit-Tracker`.

### Project relationships in the portfolio

`02-Habit-Tracker` shares port-allocation policy with sibling projects (`PORT-MAP.md` is the global authority):
- `01-*`, `02-Habit-Tracker`, `03-Nutrition-Tracker`, `04-Finance-Tracker`, `05-portfolio-data-platform`, etc.
- `02` web ports: 3020/8020. Shares Postgres + Redis instances from `05`.
- `04` is the iOS visual reference. `03` (Nutrition Tracker) reportedly has a similar iOS conversion in flight per session memory (planning docs at `03-Nutrition-Tracker/plans/`).

### Workflow philosophy reminder (per CLAUDE.md)

After completing each step, ALWAYS tell the user:
1. What was just completed.
2. The next command name.
3. Exactly what to type/say.

Example after Task 0.1 commits:
> ✅ Task 0.1 complete. Build green, 2 smoke tests passing, commit `<sha>`. Next: `/build slice-00 task 0.2 — Theme system foundation`.

### Parallel session warning

This project lives next to `03-Nutrition-Tracker` and `04-Finance-Tracker`, which are also in active iOS conversion. **Do not cross-edit between them.** When reading sibling `04` for reference, only Read — never Write.

### One-screen recap for the new session

```
WHERE WE ARE
  Web Habit Tracker MVP exists, runs locally, never shipped.
  Decided to add native iOS 26 app + web admin sharing one FastAPI backend.
  SPEC.md written. 12 slice plans written (plans/). Slice 0 Task 0.1 scaffolded.

WHAT'S DONE
  ios/project.yml, ios/HabitTracker/HabitTrackerApp.swift, ios/HabitTracker/RootView.swift,
  ios/HabitTrackerTests/SmokeTest.swift, ios/.gitignore — all present.
  xcodegen generate succeeded → ios/HabitTracker.xcodeproj exists.
  sudo xcode-select switch to Xcode.app — done (verified 2026-06-04).

WHAT'S BLOCKED
  Original handoff's destination string ('iPhone 16 Pro' / 'OS=26.0') is invalid.
  Installed Xcode is 26.4; installed iPhone sims are 17 series on iOS 26.4 only.
  Need user OK to switch to 'iPhone 17 Pro' / 'OS=26.4' OR install older platform.

WHAT'S NEXT
  Confirm destination string → xcodebuild build → xcodebuild test → commit Task 0.1
  → start Task 0.2 (theme system, mirroring sibling 04).
```

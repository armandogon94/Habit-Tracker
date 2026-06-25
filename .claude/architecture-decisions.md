# Key Architectural Decisions

## Computed Streaks (not stored)

**Decision:** Calculate streaks on-the-fly from `habit_logs` table instead of maintaining a separate `streaks` table.

- **Why:** Single source of truth — no sync issues. Algorithm walks backward from today counting consecutive completed dates.
- **Status:** IMPLEMENTED in `backend/app/services/streak_service.py`. Verified working.
- **Trade-off:** Slightly more compute per request, but trivial for personal use. Cache in Redis (DB#2) if needed.
- **See:** `.claude/memory.md` § [Architect] Computed Streaks Over Stored Streaks

## RRULE Scheduling (RFC 5545) — DAILY-ONLY for now

**Decision (2026-06-24):** Keep the `rrule` text column but enforce daily-only at
the API layer until real scheduling is built. Streak, calendar, and analytics
logic all assume every calendar day is a due occurrence (PLAN.md lines 287-341),
so a non-daily rule would silently miscount. Rather than ship an unhonored
contract, `HabitCreate`/`HabitUpdate` now reject any rrule other than the
canonical `FREQ=DAILY` (`app/schemas/habit.py::normalize_daily_rrule`).

- **Accepted:** `FREQ=DAILY` (case-insensitive, tolerates a `RRULE:` prefix /
  trailing `;` / `INTERVAL=1`). Everything else → 422.
- **Deferred (option b):** real RRULE support via `dateutil.rrule` —
  schedule-aware streak breaks (only on a missed *due* occurrence),
  per-occurrence calendar marking, and due-day completion-rate denominators.
  No frontend UI exposes non-daily schedules yet, so this is intentionally YAGNI.
- **Tests:** `backend/tests/schemas/test_habit_rrule.py`,
  `backend/tests/services/test_streak_service.py`.
- **Status:** ENFORCED. Field kept (no migration); the daily algorithm is
  unchanged but now extracted into pure, unit-tested helpers.

## Timezone Handling

**Decision:** Store dates in user's local timezone; timestamps in UTC.

- `completed_date` as `DATE` (user's local date) — daily reset at user's midnight
- All other timestamps as `TIMESTAMPTZ` (UTC with timezone info)
- User's IANA timezone in `users.timezone` (e.g., `America/Los_Angeles`)
- **Status:** IMPLEMENTED in models and database schema.
- **See:** `.claude/memory.md` § [DBA] Timezone Strategy

## Custom JWT Authentication

**Decision:** Roll our own JWT (not FastAPI-Users — in maintenance mode).

- **Access token:** 15 min lifetime, stored in React state (memory, NOT localStorage)
- **Refresh token:** 7 day lifetime, stored in httpOnly cookie (OWASP best practice)
- **Whitelist approach:** tokens tracked in Redis for immediate revocation (NOT YET IMPLEMENTED)
- **Implementation:** `backend/app/core/security.py` using `python-jose` + `bcrypt`
- **Note:** Switched from `passlib[bcrypt]` to raw `bcrypt` due to incompatibility with bcrypt 5.0+.
- **See:** `.claude/memory.md` § [Security] Custom JWT Auth

## Hybrid Data Fetching

**Decision:** TanStack Query for all client-side state management; consider RSCs for initial page loads later.

- No Redux — TanStack Query + React context covers all state needs
- Server components by default; add `'use client'` only when needed
- **Status:** PARTIALLY IMPLEMENTED. TanStack Query works for all data.
- **See:** RESEARCH-FINDINGS.md § Next.js 14+ App Router

## Analytics

**Decision:** Currently computed on-the-fly; upgrade to materialized views when performance requires it.

- Real-time streak computation for current data (fast enough for MVP)
- Materialized views for monthly summaries (completion rate, totals) — refreshed daily via scheduled task (TODO)
- **See:** `.claude/memory.md` § [DBA] Analytics via Materialized Views

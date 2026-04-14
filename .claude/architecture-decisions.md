# Key Architectural Decisions

## Computed Streaks (not stored)

**Decision:** Calculate streaks on-the-fly from `habit_logs` table instead of maintaining a separate `streaks` table.

- **Why:** Single source of truth — no sync issues. Algorithm walks backward from today counting consecutive completed dates.
- **Status:** IMPLEMENTED in `backend/app/services/streak_service.py`. Verified working.
- **Trade-off:** Slightly more compute per request, but trivial for personal use. Cache in Redis (DB#2) if needed.
- **See:** `.claude/memory.md` § [Architect] Computed Streaks Over Stored Streaks

## RRULE Scheduling (RFC 5545)

**Decision:** Use iCalendar RRULE format stored as text field.

- **Formats:**
  - Daily: `FREQ=DAILY`
  - Weekdays: `FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR`
  - Custom: `FREQ=WEEKLY;BYDAY=MO,WE,FR`

- **Libraries:** `dateutil.rrule` (Python), `rrule` (npm)
- **Status:** IMPLEMENTED — habits table has `rrule` column. Streak calculation NOT yet schedule-aware (TODO).
- **See:** `.claude/memory.md` § [Architect] RRULE for Habit Scheduling

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

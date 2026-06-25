# Slice 04 — Backend RRULE-aware streaks + composite indexes

> **Implements:** SPEC §11 tech debt items 2 + 6, §8 backend criterion "weekday-only habit doesn't break streak on weekend"
> **Status:** READY (depends on Slice 03 for real client to verify; technically can run after Slice 01)
> **Estimated sessions:** 2
> **Unblocks:** Slice 05 (offline streak computation must match server)

---

## 1. Objective

Rewrite `streak_service.py` so streak calculation respects each habit's RRULE schedule. Today, a weekday-only habit (`FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR`) breaks its streak every Saturday because the algorithm naively walks day-by-day. After this slice, the algorithm asks: "what's the previous *scheduled* date before today?" — Saturdays/Sundays are skipped for weekday habits, off-days are skipped for weekly habits. Add composite DB indexes that the new algorithm relies on. Comprehensive unit tests with parametrized RRULE × log patterns. This is a `deprecation-and-migration` slice — old behavior changes; we snapshot existing behavior in a regression test before changing it, so the change is auditable.

## 2. Pre-conditions

- [ ] Slice 01 done (env, role, mobile auth — unrelated but co-located backend work)
- [ ] Slice 03 done — iOS shows real streak values, so visual regression is observable
- [ ] `dateutil` already in dependencies (it is — used by `dateutil.rrule`)

## 3. Files to create / modify

### Modify
- `backend/app/services/streak_service.py` — rewrite both functions to be RRULE-aware
- `backend/app/services/habit_service.py` — pass `habit.rrule` into streak helpers
- `backend/app/routers/habits.py` — no signature change; just verify behavior

### Create
- `backend/app/services/schedule.py` — pure helper: `expected_dates(rrule_str, start, end, anchor) -> list[date]`, `previous_scheduled_date(rrule_str, before_date, anchor) -> date | None`, `is_scheduled(rrule_str, on_date, anchor) -> bool`
- `backend/alembic/versions/<auto>_add_composite_indexes.py` — composite indexes on `habit_logs(habit_id, completed_date DESC)` and `habit_logs(habit_id, completed_date)` for range scans
- `backend/tests/services/test_streak_service.py` — comprehensive parametrized tests (RED first)
- `backend/tests/services/test_schedule.py` — pure helper tests
- `backend/tests/services/test_streak_service_regression.py` — snapshot of OLD behavior on existing seed data, kept for audit
- `docs/adr/0001-rrule-aware-streaks.md` — ADR documenting the change and rationale

---

## 4. Tasks

### Task 4.1 — Schedule helper module + tests

**Description:** Pure date functions. No DB. Heavy use of `dateutil.rrule`.

**Acceptance:**
- [ ] `expected_dates("FREQ=DAILY", date(2026,4,1), date(2026,4,30), anchor)` returns 30 dates
- [ ] `expected_dates("FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR", …)` returns weekdays only
- [ ] `expected_dates("FREQ=WEEKLY;BYDAY=MO,WE,FR", …)` returns 3 dates per week
- [ ] `previous_scheduled_date("FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR", before=Sat, anchor=anchor) == Friday`
- [ ] `is_scheduled` consistent with `expected_dates`
- [ ] All `test_schedule.py` GREEN
- [ ] Edge cases: anchor in future, anchor in past, DST boundary

**Verify:** `uv run pytest tests/services/test_schedule.py -v`

**Files:** `app/services/schedule.py`, `tests/services/test_schedule.py`

**Skills:** `test-driven-development`, `source-driven-development` (RFC 5545 + dateutil docs), `code-simplification` (keep functions tiny + pure)

---

### Task 4.2 — Snapshot existing streak behavior (regression test)

**Description:** Before changing the algorithm, capture what it produces on the seeded demo data. This regression file documents the old behavior; we don't expect it to keep passing — but a diff in PR makes the change auditable.

**Acceptance:**
- [ ] `test_streak_service_regression.py` runs against demo seed user; asserts current streak values per habit (e.g., habit A → 8, habit B → 0)
- [ ] Tests GREEN today
- [ ] After Task 4.3, expected to FAIL — that's the audit signal
- [ ] File contains comment explaining "this file documents pre-RRULE behavior; updated values in Task 4.3"

**Verify:** `uv run pytest tests/services/test_streak_service_regression.py -v` GREEN before task 4.3.

**Files:** `tests/services/test_streak_service_regression.py`

**Skills:** `test-driven-development`, `deprecation-and-migration`

---

### Task 4.3 — Rewrite streak algorithm + new tests

**Description:** New `compute_current_streak` and `compute_longest_streak` that consult `schedule.previous_scheduled_date`. Walk backward through SCHEDULED dates only.

**Acceptance:**
- [ ] `compute_current_streak(db, habit, today)` walks backward only through dates where `is_scheduled(habit.rrule, d, habit.created_at)` is True
- [ ] Weekday habit logged Mon–Fri → 5-day streak unbroken on Saturday
- [ ] Weekly MWF habit logged correctly → counts only those 3 days/week
- [ ] Daily habit behavior unchanged (regression of regression)
- [ ] `compute_longest_streak` mirror update
- [ ] `test_streak_service.py` parametrized over (rrule, log pattern, expected) with ≥15 cases
- [ ] All GREEN
- [ ] `test_streak_service_regression.py` updated with new expected values; both committed in same commit

**Verify:** `uv run pytest tests/services/test_streak_service.py tests/services/test_streak_service_regression.py -v`. Live: weekday habit on iOS shows uninterrupted streak through weekend.

**Files:** `app/services/streak_service.py`, `app/services/habit_service.py` (pass rrule), `tests/services/test_streak_service.py`, `tests/services/test_streak_service_regression.py` (update expected values)

**Skills:** `test-driven-development`, `code-simplification`, `deprecation-and-migration`, `performance-optimization` (avoid N round-trips to DB)

---

### Task 4.4 — Composite indexes migration

**Description:** Add `(habit_id, completed_date DESC)` and `(habit_id, completed_date)`. Streak queries now do single-index range scans.

**Acceptance:**
- [ ] Migration file created and reviewed
- [ ] `EXPLAIN ANALYZE` on `SELECT completed_date FROM habit_logs WHERE habit_id = ... ORDER BY completed_date DESC LIMIT 365` shows index scan, not seq scan
- [ ] Migration tested on local DB; reversible
- [ ] No data loss, no schema renames

**Verify:**
```bash
uv run alembic upgrade head
psql habits_db -c "EXPLAIN ANALYZE SELECT completed_date FROM habit_logs WHERE habit_id = '<uuid>' ORDER BY completed_date DESC LIMIT 365;"
```

**Files:** `alembic/versions/<auto>_add_composite_indexes.py`

**Skills:** `database-migrations`, `performance-optimization`, `source-driven-development` (PG index docs)

---

### Task 4.5 — ADR documenting the change

**Description:** Architecture Decision Record explaining: what changed, why, performance impact, rollback path.

**Acceptance:**
- [ ] `docs/adr/0001-rrule-aware-streaks.md` exists
- [ ] Sections: Context, Decision, Consequences, Alternatives Considered, Rollback Plan
- [ ] Linked from CLAUDE.md and SPEC.md §11

**Verify:** `cat docs/adr/0001-rrule-aware-streaks.md`

**Files:** `docs/adr/0001-rrule-aware-streaks.md`, `CLAUDE.md` (link), `SPEC.md` (link)

**Skills:** `documentation-and-adrs`

---

## 5. Test plan (RED → GREEN order)

| File | Cases | Phase |
|---|---|---|
| `test_schedule.py` | `test_daily_30_days`, `test_weekdays_skips_weekend`, `test_weekly_mwf`, `test_previous_scheduled_daily`, `test_previous_scheduled_weekday_from_saturday`, `test_previous_scheduled_weekly_mwf`, `test_is_scheduled_matches_expected`, `test_dst_boundary`, `test_anchor_in_future_returns_empty` | 4.1 (RED first) |
| `test_streak_service_regression.py` | `test_current_streak_demo_user_legacy_behavior` (passes pre-4.3, updated post-4.3) | 4.2 (RED→GREEN both phases) |
| `test_streak_service.py` | `test_daily_unbroken_n_days`, `test_daily_one_miss_breaks`, `test_weekday_habit_unbroken_through_weekend`, `test_weekly_mwf_correct_streak`, `test_today_incomplete_uses_yesterday`, `test_no_logs_returns_zero`, `test_logs_in_future_ignored`, `test_longest_handles_gaps_correctly`, `test_longest_weekday_habit`, `test_anchor_before_creation_safety`, parametrized matrix of (rrule, days, expected) | 4.3 (RED first) |

---

## 6. Skills mapping

| Task | Primary | Secondary |
|---|---|---|
| 4.1 | `test-driven-development`, `source-driven-development`, `code-simplification` | — |
| 4.2 | `test-driven-development`, `deprecation-and-migration` | — |
| 4.3 | `test-driven-development`, `code-simplification`, `deprecation-and-migration`, `performance-optimization` | — |
| 4.4 | `database-migrations`, `performance-optimization`, `source-driven-development` | — |
| 4.5 | `documentation-and-adrs` | — |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Algorithm change surprises existing users (streak numbers shift) | Med | Demo to user before deploy; ADR documents rationale; consider one-time announcement in app |
| RRULE parsing edge case (uncommon pattern) breaks calculation | Med | Restrict to 3 supported RRULEs in v1; raise on unknown patterns; future expansion when needed |
| Composite index migration locks `habit_logs` on prod | Low (small data) | Migration runs in seconds at our scale; consider `CONCURRENTLY` if data grows |
| `dateutil.rrule` imprecise around DST | Low | Tests cover spring-forward/fall-back day; we always store DATE not DATETIME for log dates |
| Walking backward day-by-day is slow with large history | Med | Composite index makes single query fetch all needed dates; algorithm walks Python-side over fixed-size set |

---

## 8. Definition of done

- [ ] All test files in §5 GREEN
- [ ] Demo: weekday habit logged Mon–Fri shows uninterrupted streak in iOS through Saturday + Sunday
- [ ] `EXPLAIN ANALYZE` confirms index use
- [ ] ADR committed and linked
- [ ] Slice committed: `feat(backend): rrule-aware streak computation + composite indexes`
- [ ] User reviewed; CHECKPOINT C (combined with slice 05)

## 9. Estimated session count

**2 sessions:**
- Session 1: Tasks 4.1 + 4.2 + 4.5 (schedule helper + regression snapshot + ADR)
- Session 2: Tasks 4.3 + 4.4 (rewrite + indexes)

## 10. What unblocks the next slice

- Backend streak math is now correct → iOS offline streak computation in slice 05 can mirror this exactly
- Composite indexes installed → calendar/analytics endpoints scale better
- ADR documents the algorithm — future maintenance has context

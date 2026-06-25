# Slice 08 — iOS Live Activity for timed habits (ActivityKit)

> **Implements:** SPEC §1 Live Activity + §9 Q1 (simple v1: start, tick, end, no pause)
> **Status:** READY (depends on Slice 05; recommended after Slice 07)
> **Estimated sessions:** 2
> **Unblocks:** None

---

## 1. Objective

Some habits are **timed** — "Meditate 10 min", "Read 30 min". Add an optional `targetDuration: TimeInterval?` to habits. When the user starts a timed habit, show a Live Activity in the Dynamic Island and Lock Screen that ticks down (1-minute granularity), shows progress, and offers a "Stop" button. On completion, the habit is auto-logged. Simple v1: start → tick → end. No pause/resume. Uses ActivityKit. The activity is started by the main app, updated on a 60-second background timer (or earlier on user end), and ended explicitly.

## 2. Pre-conditions

- [ ] Slice 05 done — repo + write queue
- [ ] Slice 07 done (recommended for shared App Group patterns)
- [ ] iOS 26 simulator supports ActivityKit (it does; iOS 16.1+)

## 3. Files to create / modify

### Backend (small additive)
- `backend/app/models/habit.py` — `target_duration_seconds: int | None`
- `backend/alembic/versions/<auto>_add_target_duration.py`
- `backend/app/schemas/habit.py` + `routers/habits.py` — round-trip
- `backend/tests/routers/test_target_duration.py`

### iOS new extension target
- Add `HabitTrackerLiveActivity` widget extension target in `ios/project.yml` (or include in existing `HabitTrackerWidget` target — Apple recommends sharing where possible)

### Create
- `ios/HabitTracker/Core/LiveActivity/HabitTimerAttributes.swift` — `ActivityAttributes` static + dynamic state (`targetDate`, `habitName`, `themeID`)
- `ios/HabitTracker/Core/LiveActivity/HabitTimerActivityManager.swift` — actor; `start(for habit:)`, `tick(_)`, `end(_)`; idempotent
- `ios/HabitTrackerWidget/LiveActivities/HabitTimerLiveActivityView.swift` — Lock screen view + Dynamic Island regions
- `ios/HabitTracker/Features/HabitDetail/StartTimerButton.swift` — visible only if `habit.targetDuration != nil`
- `ios/HabitTracker/Features/CreateEdit/TargetDurationPicker.swift` — picker (off / 5 / 10 / 15 / 20 / 30 / 45 / 60 min)
- `ios/HabitTracker/Core/LiveActivity/StopTimerIntent.swift` — `AppIntent` triggered by activity Stop button

### Modify
- `Features/CreateEdit/CreateHabitSheet.swift` and `EditHabitSheet.swift` — add TargetDurationPicker
- `Features/HabitDetail/HabitDetailView.swift` — show StartTimerButton when applicable
- `HabitTrackerApp.swift` — handle deep link from activity tap; on app foreground, reconcile any orphaned activities (end them)

### Tests
- `ios/HabitTrackerTests/HabitTimerActivityManagerTests.swift` — start/end semantics, idempotency
- `ios/HabitTrackerTests/StopTimerIntentTests.swift`
- `backend/tests/routers/test_target_duration.py`

---

## 4. Tasks

### Task 8.0 — Backend target_duration column

**Acceptance:**
- [ ] Column added, nullable
- [ ] DTO + endpoints accept it
- [ ] Tests cover round-trip

**Verify:** `uv run pytest tests/routers/test_target_duration.py -v`

**Files:** `app/models/habit.py`, `alembic/versions/<auto>_add_target_duration.py`, `app/schemas/habit.py`, `app/routers/habits.py`, `tests/routers/test_target_duration.py`

**Skills:** `database-migrations`, `api-and-interface-design`, `test-driven-development`

---

### Task 8.1 — HabitTimerAttributes + LiveActivity view (UI scaffold)

**Description:** Define attributes; build Lock Screen + Dynamic Island views. No state mutation yet — just visual.

**Acceptance:**
- [ ] `ActivityAttributes` defined with `static` (habit name, theme id) + `ContentState` (target date, started date)
- [ ] Lock Screen view: habit name + circular progress + remaining time
- [ ] Dynamic Island compact: tiny progress
- [ ] Dynamic Island expanded: full circular progress + Stop button
- [ ] Both themes themed via WidgetTheme from slice 07
- [ ] Manually trigger activity from a debug menu in Settings

**Verify:** Live in simulator (Xcode 16+ supports Dynamic Island in iPhone 15+ sim).

**Files:** `Core/LiveActivity/HabitTimerAttributes.swift`, `HabitTrackerWidget/LiveActivities/HabitTimerLiveActivityView.swift`

**Skills:** `swiftui-patterns`, `liquid-glass-design`, `ios-hig-design`, `source-driven-development` (ActivityKit + Dynamic Island docs)

---

### Task 8.2 — HabitTimerActivityManager (start/tick/end)

**Description:** Actor wrapping `Activity<HabitTimerAttributes>`. Handles lifecycle.

**Acceptance:**
- [ ] `start(for habit:)` requests activity with target = now + duration
- [ ] `tick()` updates ContentState (used minimally; SwiftUI `Text(timerInterval:)` does most updating)
- [ ] `end()` finishes activity, optionally with `dismissalPolicy: .immediate` on user-stop or `.after(60s)` on timer-end
- [ ] On `end` due to timer expiration → auto-log the habit via repo
- [ ] Idempotency: starting twice for same habit ends old then starts new
- [ ] All `HabitTimerActivityManagerTests` GREEN

**Verify:** Live: start timer for 1 min → activity appears → at 1 min, habit auto-logged + activity ends.

**Files:** `Core/LiveActivity/HabitTimerActivityManager.swift`, `HabitTrackerTests/HabitTimerActivityManagerTests.swift`

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development`, `source-driven-development`

---

### Task 8.3 — UI: TargetDurationPicker + StartTimerButton

**Description:** Wire user-facing controls.

**Acceptance:**
- [ ] CreateHabitSheet/EditHabitSheet show TargetDurationPicker
- [ ] HabitDetailView shows StartTimerButton if `targetDuration != nil`
- [ ] Tap → `HabitTimerActivityManager.start(for:)` → activity appears in real time
- [ ] If activity already running, button shows "Stop" instead

**Verify:** Live; both themes.

**Files:** `Features/CreateEdit/TargetDurationPicker.swift`, `CreateHabitSheet.swift`, `EditHabitSheet.swift`, `Features/HabitDetail/StartTimerButton.swift`, `HabitDetailView.swift`

**Skills:** `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design`, `frontend-ui-engineering`

---

### Task 8.4 — StopTimerIntent (AppIntent)

**Description:** "Stop" button in activity → AppIntent → manager.end().

**Acceptance:**
- [ ] `StopTimerIntent` calls `HabitTimerActivityManager.end(habitID:wasCompleted:false)`
- [ ] If user stops early, habit is NOT auto-logged
- [ ] Tests verify intent path

**Verify:** Live; tap Stop in Dynamic Island → activity ends, no log.

**Files:** `Core/LiveActivity/StopTimerIntent.swift`, `HabitTrackerTests/StopTimerIntentTests.swift`

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`, `swiftui-patterns`, `test-driven-development`

---

### Task 8.5 — Reconciliation on app foreground

**Description:** If app crashes mid-timer, on next foreground end any orphaned activities and decide whether to log.

**Acceptance:**
- [ ] On `.didBecomeActive`, walk `Activity<HabitTimerAttributes>.activities`; if `targetDate < now`, treat as completed → log + end; if still in future, leave running

**Verify:** Force-kill app mid-timer → relaunch after timer would have ended → activity is gone, habit logged.

**Files:** `HabitTrackerApp.swift`, `Core/LiveActivity/HabitTimerActivityManager.swift`

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`

---

## 5. Test plan

| File | Cases | Phase |
|---|---|---|
| `test_target_duration.py` (backend) | `test_create_with_target_duration`, `test_update_clears_target_duration`, `test_list_returns_target_duration` | 8.0 |
| `HabitTimerActivityManagerTests.swift` | `testStartCreatesActivity`, `testStartTwiceReplaces`, `testEndOnExpirationLogsHabit`, `testEndOnUserStopDoesNotLog`, `testReconcileOrphanedExpired` | 8.2, 8.5 |
| `StopTimerIntentTests.swift` | `testStopIntentEndsActivityWithoutLog` | 8.4 |

---

## 6. Skills mapping

| Task | Primary | Secondary |
|---|---|---|
| 8.0 | `database-migrations`, `api-and-interface-design`, `test-driven-development` | — |
| 8.1 | `swiftui-patterns`, `liquid-glass-design`, `ios-hig-design`, `source-driven-development` | — |
| 8.2 | `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development`, `source-driven-development` | — |
| 8.3 | `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design`, `frontend-ui-engineering` | — |
| 8.4 | `swift-actor-persistence`, `swift-concurrency-6-2`, `swiftui-patterns`, `test-driven-development` | — |
| 8.5 | `swift-actor-persistence`, `swift-concurrency-6-2` | — |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| ActivityKit auth not granted by user | Med | Show in-app explanation before requesting; degrade gracefully (button still works for timer in-app) |
| Background tick missed when app suspended | Low | SwiftUI `Text(timerInterval:)` updates from system clock; no app code needed |
| Multiple habits running timers simultaneously | Med | Allowed; each gets its own activity |
| Activity persists past habit deletion | Low | On habit delete, manager ends any associated activity |
| Auto-log fires while user is genuinely away → wrong day | Low | targetDate timezone-locked at start; logs use start date |
| Dynamic Island regions differ per device class | Med | Test on iPhone 15+ sim; fallback to compact only on older shapes |

---

## 8. Definition of done

- [ ] All test files in §5 GREEN
- [ ] Demo: create timed habit (5 min) → tap Start → activity appears → wait → activity ends + habit logged
- [ ] Stop early → activity ends, habit NOT logged
- [ ] Force-kill mid-timer → relaunch later → orphan reconciled correctly
- [ ] Both themes look correct in lock screen + Dynamic Island
- [ ] Slice committed: `feat(ios): live activity for timed habits with auto-log on completion`

## 9. Estimated session count

**2 sessions:**
- Session 1: Tasks 8.0 + 8.1 + 8.2 (backend + view + manager)
- Session 2: Tasks 8.3 + 8.4 + 8.5 (UI + intent + reconciliation)

## 10. What unblocks the next slice

- All major iOS-native features done — slice 09 (i18n) has the full string surface to translate
- iOS app feature-complete for v1 from a functional standpoint

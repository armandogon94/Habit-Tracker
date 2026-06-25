# Slice 06 — iOS local notifications + per-habit reminders

> **Implements:** SPEC §1 "local notifications + 1 widget" v1 scope, §8 "per-habit reminder fires at scheduled local time"
> **Status:** READY (depends on Slice 05 — reads `PersistedHabit.reminderTime`)
> **Estimated sessions:** 2
> **Unblocks:** None directly; can run in parallel with slices 07, 08, 09

---

## 1. Objective

Schedule a daily local notification per habit that has a `reminderTime` set, respecting its RRULE schedule (a weekday-only habit shouldn't fire on Saturday). Use `UserNotifications`. Notifications open straight to the relevant habit row in TodayView and offer a **"Mark done" action** so the user can complete the habit from the notification without opening the app. Reschedule on app foreground, on habit edit/create, and on RRULE change. Permission flow integrates with the FirstRunSheet from Slice 00.

## 2. Pre-conditions

- [ ] Slice 05 done — `PersistedHabit` has `reminderTime: Date?` and store is reachable from anywhere
- [ ] FirstRunSheet from slice 00 already requests `UNAuthorizationOptions.alert .sound .badge`
- [ ] Backend stores `reminder_time` per habit (add column if missing — see Task 6.0)

## 3. Files to create / modify

### Backend (small additive)
- `backend/app/models/habit.py` — add `reminder_time: time | None`
- `backend/alembic/versions/<auto>_add_reminder_time.py` — new column
- `backend/app/schemas/habit.py` — include `reminder_time` in DTOs
- `backend/app/routers/habits.py` — accept on create/update
- `backend/tests/routers/test_habits.py` — add reminder_time to factory + tests

### iOS Create
- `ios/HabitTracker/Core/Notifications/NotificationScheduler.swift` — actor; `scheduleAll()`, `schedule(for habit:)`, `cancel(for habitID:)`, `handleAction(_:for:)`; uses `UNCalendarNotificationTrigger` with `DateComponents` per scheduled day
- `ios/HabitTracker/Core/Notifications/NotificationCategory.swift` — defines "MARK_DONE" action category
- `ios/HabitTracker/Core/Notifications/NotificationRouter.swift` — `UNUserNotificationCenterDelegate` impl; routes tap → deep link, action → call repo
- `ios/HabitTracker/Features/Settings/NotificationSettingsView.swift` — toggle "Send reminders" master + view per-habit reminders + permission state
- `ios/HabitTracker/Features/CreateEdit/ReminderTimePicker.swift` — `DatePicker` (.hourAndMinute), optional (toggleable)

### Modify
- `Features/CreateEdit/CreateHabitSheet.swift` and `EditHabitSheet.swift` — add ReminderTimePicker, persist via repo
- `Core/Persistence/HabitRepository.swift` — on habit create/update/delete, call `NotificationScheduler.schedule/cancel`
- `HabitTrackerApp.swift` — register NotificationCategory at launch; set NotificationRouter as delegate; on `.didBecomeActive`, call `scheduleAll()`
- `Features/Settings/SettingsView.swift` — link to NotificationSettingsView

### Tests
- `ios/HabitTrackerTests/NotificationSchedulerTests.swift` — scheduling logic (time + RRULE → DateComponents), idempotency, cancellation
- `ios/HabitTrackerTests/NotificationRouterTests.swift` — action routing
- `backend/tests/routers/test_reminder_time.py` — round-trip

---

## 4. Tasks

### Task 6.0 — Backend: reminder_time column

**Description:** Persist reminder time on backend for cross-device consistency.

**Acceptance:**
- [ ] `habits.reminder_time` (TIME, nullable) added
- [ ] DTO + endpoints accept it
- [ ] Tests cover round-trip

**Verify:** `uv run pytest tests/routers/test_reminder_time.py -v`

**Files:** `backend/app/models/habit.py`, `alembic/versions/<auto>_add_reminder_time.py`, `app/schemas/habit.py`, `app/routers/habits.py`, `tests/routers/test_reminder_time.py`, `tests/factories.py`

**Skills:** `database-migrations`, `api-and-interface-design`, `test-driven-development`

---

### Task 6.1 — NotificationScheduler core + tests

**Description:** Pure scheduling logic. Given a habit with RRULE + reminder_time, produce N `UNNotificationRequest`s.

**Acceptance:**
- [ ] `schedule(for: PersistedHabit)`:
  - If no reminderTime → no notifications
  - Daily RRULE → 1 repeating trigger at that time
  - Weekday RRULE → 5 separate triggers (one per weekday) using `DateComponents(weekday: …)`
  - Weekly MWF → 3 triggers
- [ ] `cancel(for habitID:)` removes all by identifier prefix `habit-{id}-*`
- [ ] `scheduleAll()` reads SwiftData, cancels everything, reschedules all
- [ ] Idempotent: running `scheduleAll()` twice yields same pending requests
- [ ] All tests GREEN

**Verify:** `⌘U`; live: schedule for 1 minute from now → notification fires.

**Files:** `Core/Notifications/NotificationScheduler.swift`, `Core/Notifications/NotificationCategory.swift`, `HabitTrackerTests/NotificationSchedulerTests.swift`

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development`, `source-driven-development` (UserNotifications docs)

---

### Task 6.2 — NotificationRouter (delegate)

**Description:** Handle taps and the "Mark done" inline action.

**Acceptance:**
- [ ] Tap on notification → app opens, navigates to that habit's detail (or focuses row in Today)
- [ ] "Mark done" action → calls `HabitRepository.toggle(habit:on:today)` without opening UI; repeats if app cold
- [ ] Tested with `XCTNotificationCenterMock` (or fake NotificationCenter wrapper protocol) for action routing

**Verify:** Live: trigger notification, tap "Mark done" from lock screen → habit logged on app open.

**Files:** `Core/Notifications/NotificationRouter.swift`, `HabitTrackerApp.swift`, `HabitTrackerTests/NotificationRouterTests.swift`

**Skills:** `swift-actor-persistence`, `swiftui-patterns`, `swift-concurrency-6-2`, `test-driven-development`

---

### Task 6.3 — UI: ReminderTimePicker + Settings

**Description:** Per-habit reminder picker and a settings page.

**Acceptance:**
- [ ] CreateHabitSheet and EditHabitSheet show ReminderTimePicker (toggle + DatePicker hour/minute)
- [ ] NotificationSettingsView lists every habit with reminderTime, shows "Notifications {On|Off}" with system permission state
- [ ] If notifications permission denied: show "Open Settings" button → `UIApplication.openSettingsURLString`
- [ ] Both themes render cleanly

**Verify:** Live; set reminder for 2 minutes from now; verify on lock screen.

**Files:** `Features/CreateEdit/ReminderTimePicker.swift`, `CreateHabitSheet.swift`, `EditHabitSheet.swift`, `Features/Settings/NotificationSettingsView.swift`, `SettingsView.swift`

**Skills:** `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design`

---

### Task 6.4 — Repository hooks + foreground refresh

**Description:** Wire scheduler into repo lifecycle.

**Acceptance:**
- [ ] On `HabitRepository.create/update/delete` → calls scheduler appropriately
- [ ] On app `.didBecomeActive` → `scheduleAll()` (corrects drift after timezone changes, system date changes)
- [ ] Cancellation on sign-out
- [ ] Pending notification list visible in NotificationSettingsView debug section (gated to DEBUG builds)

**Verify:** Live: edit a habit's reminder time → old notification gone, new one scheduled.

**Files:** `Core/Persistence/HabitRepository.swift`, `HabitTrackerApp.swift`, `Features/Settings/NotificationSettingsView.swift`

**Skills:** `swift-actor-persistence`, `swiftui-patterns`

---

## 5. Test plan

| File | Cases | Phase |
|---|---|---|
| `test_reminder_time.py` (backend) | `test_create_with_reminder_time`, `test_update_clears_reminder_time`, `test_list_returns_reminder_time` | 6.0 |
| `NotificationSchedulerTests.swift` | `testNoReminderTimeNoRequests`, `testDailyOneRequest`, `testWeekdayFiveRequests`, `testWeeklyMWFThreeRequests`, `testCancelByHabitID`, `testScheduleAllIsIdempotent`, `testInvalidRRULEDoesntCrash` | 6.1 |
| `NotificationRouterTests.swift` | `testTapOpensDetailDeepLink`, `testMarkDoneActionLogsHabit`, `testActionFromLockScreenWhileAppDead` | 6.2 |

---

## 6. Skills mapping

| Task | Primary | Secondary |
|---|---|---|
| 6.0 | `database-migrations`, `api-and-interface-design`, `test-driven-development` | — |
| 6.1 | `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development`, `source-driven-development` | — |
| 6.2 | `swift-actor-persistence`, `swiftui-patterns`, `test-driven-development` | — |
| 6.3 | `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design` | — |
| 6.4 | `swift-actor-persistence`, `swiftui-patterns` | — |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Notification limit (64 pending per app) | Med | 6 habits × max 7 weekday triggers = 42 — under limit. Document; warn user if exceeded |
| Time zone change at runtime breaks schedules | Med | `scheduleAll()` on `.didBecomeActive` re-anchors |
| User toggles "Don't allow" mid-flow | Med | Detect via `getNotificationSettings()`; show open-settings CTA in NotificationSettingsView |
| "Mark done" action fires when offline | Low | Repo write goes to queue (slice 05); syncs later |
| Notification fires while app open and is annoying | Low | Set `UNNotificationPresentationOptions = [.banner, .list, .sound]`; user controls |
| RRULE change leaves stale notifications | Med | Repo update hook always cancels + reschedules |

---

## 8. Definition of done

- [ ] All test files in §5 GREEN
- [ ] Demo: set 3 habits with reminder times 1–3 min from now; all fire correctly
- [ ] Tap "Mark done" from notification → habit logged
- [ ] NotificationSettingsView accurate (permission state + per-habit list)
- [ ] Editing reminder time updates schedule immediately
- [ ] Slice committed: `feat(ios): per-habit local notifications + reminder UI`

## 9. Estimated session count

**2 sessions:**
- Session 1: Tasks 6.0 + 6.1 (backend column + scheduler core)
- Session 2: Tasks 6.2 + 6.3 + 6.4 (router + UI + hooks)

## 10. What unblocks the next slice

- None directly. Slice 07 (widget) and 08 (Live Activity) and 09 (i18n) can each start independently after this.
- Notification permission flow proven works end-to-end → onboarding flow validated

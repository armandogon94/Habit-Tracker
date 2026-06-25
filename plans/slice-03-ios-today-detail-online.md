# Slice 03 — iOS Today + HabitDetail wired to backend (online only)

> **Implements:** SPEC §1 iOS user flow, §2 iOS networking, §8 iOS criteria (toggle persists, screens render)
> **Status:** READY (depends on Slice 02)
> **Estimated sessions:** 3
> **Unblocks:** Slice 04 (RRULE-aware streaks needs real client to verify), Slice 05 (offline overlay needs working online flow first), Slice 06–08 (need real habits to attach reminders/widget/Live Activity)

---

## 1. Objective

Replace `MockData` in Today, HabitDetail, Analytics, and CreateEdit with real backend data. Build `HabitsService` on top of `APIClient`. All habit CRUD + log toggle + analytics + heatmap data flows through real HTTP. Online only — no offline cache yet (slice 05). Optimistic UI on toggle: flip locally, fire request, reconcile on response. After this slice, the iOS app is functionally equivalent to the web app, just nicer.

## 2. Pre-conditions

- [ ] Slice 02 done — auth works
- [ ] Backend habits routes operational (`/habits/`, `/habits/{id}`, `/habits/{id}/log`, `/habits/{id}/calendar`, `/habits/{id}/analytics`)
- [ ] User signed in via real flow

## 3. Files to create / modify

### Create
- `ios/HabitTracker/Core/Services/HabitsService.swift` — actor; methods: `list()`, `get(id:)`, `create(_:)`, `update(_:)`, `delete(id:)`, `log(habitID:, date:, note:)`, `unlog(habitID:, date:)`, `calendar(habitID:, from:, to:)`, `analytics(habitID:)`
- `ios/HabitTracker/Core/Networking/DTO+Habits.swift` — `HabitDTO`, `HabitLogDTO`, `CreateHabitRequest`, `UpdateHabitRequest`, `LogHabitRequest`, `CalendarResponse`, `AnalyticsResponse`
- `ios/HabitTracker/Features/Today/TodayViewModel.swift` — `@Observable @MainActor`; loads, optimistic toggle, error surface
- `ios/HabitTracker/Features/HabitDetail/HabitDetailViewModel.swift` — loads habit + calendar + analytics in parallel via `async let`
- `ios/HabitTracker/Features/CreateEdit/CreateHabitViewModel.swift` and `EditHabitViewModel.swift`
- `ios/HabitTracker/Features/Analytics/AnalyticsViewModel.swift`

### Modify
- `Features/Today/TodayView.swift` — bind to `TodayViewModel`, drop MockData refs
- `Features/Today/HabitRow.swift` — drop MockData; gets `Habit` + `isDoneToday` from VM
- `Features/HabitDetail/HabitDetailView.swift` — bind to `HabitDetailViewModel`
- `Features/HabitDetail/HeatmapCanvas.swift` — accepts `[HabitLog]` from real API
- `Features/HabitDetail/WeeklyChart.swift` — accepts `[HabitLog]` from real API
- `Features/CreateEdit/CreateHabitSheet.swift` and `EditHabitSheet.swift` — call VM
- `Features/Analytics/AnalyticsView.swift` — bind to VM

### Tests
- `ios/HabitTrackerTests/HabitsServiceTests.swift` — mocked APIClient; CRUD, optimistic + reconcile, error mapping
- `ios/HabitTrackerTests/TodayViewModelTests.swift` — load, toggle, optimistic rollback on failure
- `ios/HabitTrackerTests/HabitDetailViewModelTests.swift` — parallel load, error per channel
- `ios/HabitTrackerTests/AnalyticsViewModelTests.swift`

### Backend (small, additive)
- `backend/app/routers/habits.py` — verify response shape matches DTO; add `note` field if missing on log endpoint; document in OpenAPI
- `backend/tests/routers/test_habits.py` — happy-path coverage for endpoints iOS will hit (filling test gap)

---

## 4. Tasks

### Task 3.1 — DTOs + HabitsService + tests

**Description:** Mirror backend response shape exactly; build the service surface.

**Acceptance:**
- [ ] DTOs cover every habit endpoint response
- [ ] Service methods are async throws → typed `APIError`
- [ ] All `HabitsServiceTests` GREEN with mocked APIClient
- [ ] Backend OpenAPI docs reflect actual shape (manual check at `/docs`)

**Verify:** `⌘U`; also `curl localhost:8020/api/v1/habits/ -H "Authorization: Bearer …"` shape matches DTO.

**Files:** `Core/Services/HabitsService.swift`, `Core/Networking/DTO+Habits.swift`, `HabitTrackerTests/HabitsServiceTests.swift`, `HabitTrackerTests/Fixtures/habits-list.json`, `habit-detail.json`, `calendar.json`, `analytics.json`

**Skills:** `swift-protocol-di-testing`, `swift-concurrency-6-2`, `test-driven-development`, `api-and-interface-design` (DTO contract pinning)

---

### Task 3.2 — TodayViewModel + wire TodayView

**Description:** Replace mock with real flow. Optimistic toggle pattern.

**Acceptance:**
- [ ] On view appear, `load()` fetches today's habits
- [ ] Tap row → optimistic flip + `log` request → on failure, revert + show toast
- [ ] Hero "X of Y done today" reflects actual data
- [ ] Pull-to-refresh works
- [ ] Loading skeleton on first load
- [ ] Empty state if no habits ("Create your first habit")
- [ ] All `TodayViewModelTests` GREEN (load happy, load failure, toggle happy, toggle failure rollback)

**Verify:** Live in simulator with real backend; toggle several habits; force network failure (airplane mode mid-flight) → row reverts.

**Files:** `Features/Today/TodayViewModel.swift`, `Features/Today/TodayView.swift`, `Features/Today/HabitRow.swift`, `HabitTrackerTests/TodayViewModelTests.swift`

**Skills:** `swiftui-patterns`, `swift-concurrency-6-2`, `test-driven-development`, `frontend-ui-engineering`

---

### Task 3.3 — HabitDetailViewModel + wire HabitDetail

**Description:** Detail screen pulls habit, calendar (last 90 days), analytics in parallel.

**Acceptance:**
- [ ] `async let` parallel fetch
- [ ] Independent error states per panel (heatmap can fail without breaking weekly chart)
- [ ] Heatmap uses real log data
- [ ] WeeklyChart uses real log data, last 4 weeks
- [ ] Pull-to-refresh
- [ ] All `HabitDetailViewModelTests` GREEN

**Verify:** Live; tap a habit, see real heatmap and chart.

**Files:** `Features/HabitDetail/HabitDetailViewModel.swift`, `Features/HabitDetail/HabitDetailView.swift`, `Features/HabitDetail/HeatmapCanvas.swift`, `Features/HabitDetail/WeeklyChart.swift`, `HabitTrackerTests/HabitDetailViewModelTests.swift`

**Skills:** `swiftui-patterns`, `swift-concurrency-6-2`, `frontend-ui-engineering`

---

### Task 3.4 — CreateEdit VMs + wire sheets

**Description:** Create/edit/delete habits through real backend.

**Acceptance:**
- [ ] Create form → POST → on 201, sheet dismisses + Today refreshes
- [ ] Edit form → PUT → on 200, detail screen refreshes
- [ ] Delete with confirmation → DELETE → returns to Today
- [ ] Validation errors (422) shown inline per field
- [ ] All VM tests GREEN

**Verify:** Live: create habit → appears in Today; edit color → reflected; delete → removed.

**Files:** `Features/CreateEdit/CreateHabitViewModel.swift`, `EditHabitViewModel.swift`, `CreateHabitSheet.swift`, `EditHabitSheet.swift`, `HabitTrackerTests/CreateHabitViewModelTests.swift`, `EditHabitViewModelTests.swift`

**Skills:** `swiftui-patterns`, `swift-concurrency-6-2`, `frontend-ui-engineering`

---

### Task 3.5 — Analytics tab wired

**Description:** Aggregate analytics across all habits.

**Acceptance:**
- [ ] Cards show real numbers
- [ ] Donut chart uses real per-habit completion share
- [ ] Empty state if user has zero habits
- [ ] AnalyticsViewModelTests GREEN

**Verify:** Live; cross-check with web `/analytics` page values.

**Files:** `Features/Analytics/AnalyticsViewModel.swift`, `Features/Analytics/AnalyticsView.swift`, `HabitTrackerTests/AnalyticsViewModelTests.swift`

**Skills:** `swiftui-patterns`, `swift-concurrency-6-2`

---

### Task 3.6 — Backend test gap fill

**Description:** Add happy-path tests for endpoints iOS now consumes.

**Acceptance:**
- [ ] `tests/routers/test_habits.py` covers list, get, create, update, delete, log, unlog, calendar, analytics — happy + auth-required cases
- [ ] All GREEN

**Verify:** `uv run pytest tests/routers/test_habits.py -v`

**Files:** `backend/tests/routers/test_habits.py`, `backend/tests/factories.py` (extend if needed)

**Skills:** `test-driven-development`

---

## 5. Test plan (RED → GREEN order)

| File | Cases (named) | Phase |
|---|---|---|
| `HabitsServiceTests.swift` | `testListHappy`, `testListAuthError`, `testCreateHappy`, `testUpdateHappy`, `testDeleteHappy`, `testLogHappy`, `testUnlogHappy`, `testCalendarRange`, `testAnalyticsHappy`, `testValidationError422` | 3.1 |
| `TodayViewModelTests.swift` | `testLoadPopulatesRows`, `testToggleOptimisticRollbackOnFailure`, `testRefreshUpdatesData`, `testEmptyState` | 3.2 |
| `HabitDetailViewModelTests.swift` | `testParallelLoadAllSuccess`, `testHeatmapFailureDoesntBlockChart`, `testRefreshReloadsAll` | 3.3 |
| `CreateHabitViewModelTests.swift` | `testValidNameSubmits`, `testEmptyNameValidation`, `testServerValidationShown`, `testNetworkErrorShown` | 3.4 |
| `EditHabitViewModelTests.swift` | `testPrefillsFromHabit`, `testSubmitsUpdate`, `testDeleteConfirms` | 3.4 |
| `AnalyticsViewModelTests.swift` | `testAggregatesCorrectly`, `testEmptyState` | 3.5 |
| `test_habits.py` (backend) | `test_list_returns_user_habits`, `test_get_404_for_other_user`, `test_create_201`, `test_update_200`, `test_delete_204`, `test_log_creates_entry`, `test_log_idempotent_per_date`, `test_unlog_removes`, `test_calendar_range`, `test_analytics_shape`, `test_unauthenticated_401` | 3.6 |

---

## 6. Skills mapping

| Task | Primary | Secondary |
|---|---|---|
| 3.1 | `swift-protocol-di-testing`, `swift-concurrency-6-2`, `test-driven-development`, `api-and-interface-design` | `source-driven-development` |
| 3.2 | `swiftui-patterns`, `swift-concurrency-6-2`, `frontend-ui-engineering`, `test-driven-development` | `ios-hig-design` |
| 3.3 | `swiftui-patterns`, `swift-concurrency-6-2`, `frontend-ui-engineering` | — |
| 3.4 | `swiftui-patterns`, `swift-concurrency-6-2`, `frontend-ui-engineering` | — |
| 3.5 | `swiftui-patterns`, `swift-concurrency-6-2` | — |
| 3.6 | `test-driven-development` | `api-and-interface-design` |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| DTO drift if backend response changes | High | Pin shape in `DTOTests` with fixture JSON; backend tests verify shape; CI catches mismatch |
| Optimistic UI shows stale state on rapid taps | Med | Debounce per-habit toggle; cancel in-flight when superseded |
| Calendar fetch is slow on large data | Low (early users) | Limit to last 90 days client-side; backend has index slice 04 |
| 401 mid-fetch confuses users | Low | APIClient handles transparently; if final 401, navigate to LoginView |
| Time-zone skew (server UTC vs device local) on `completed_date` | Med | Always send local date YYYY-MM-DD; backend stores as DATE in user's tz |

---

## 8. Definition of done

- [ ] All test files in §5 GREEN (iOS + backend)
- [ ] Live demo: create habit → log → see streak update; cross-checked against web
- [ ] All MockData calls in feature views removed (only DesignPlaygroundView still uses MockData for previews)
- [ ] Pull-to-refresh works on Today and HabitDetail
- [ ] Optimistic toggle reverts cleanly on simulated network failure
- [ ] Slice committed: `feat(ios): wire Today + Detail + Analytics + CRUD to real backend`
- [ ] CHECKPOINT B reached: golden path online works end-to-end. User demos and approves.

## 9. Estimated session count

**3 sessions:**
- Session 1: Tasks 3.1 + 3.6 (service layer + backend test gap)
- Session 2: Tasks 3.2 + 3.3 (Today + Detail VMs)
- Session 3: Tasks 3.4 + 3.5 (CreateEdit + Analytics)

## 10. What unblocks the next slice

- Real habit data flows in app — slice 04 has a real iOS client to verify RRULE-aware streak behavior against
- VMs exist with optimistic patterns — slice 05 will overlay a write queue beneath the same VM API (no view changes needed)
- DTO pinning fixtures exist — future API changes are caught by test diff

# Slice 05 — iOS offline cache + write queue (SwiftData + SyncEngine)

> **Implements:** SPEC §1 "Going airplane-mode → tap habits → online → writes flush", §2 SwiftData persistence, §8 offline criterion
> **Status:** READY (depends on Slice 03; can be parallel with Slice 04)
> **Estimated sessions:** 4
> **Unblocks:** Slices 06–08 (notifications/widget/Live Activity all read SwiftData store, not network)

---

## 1. Objective

Make habit logging work offline. Add a SwiftData persistence layer mirroring backend models. Reads first hit the cache, then a background refresh from the network. Writes go into a `WriteQueue` (FIFO, persisted), processed by a `SyncEngine` whenever the network is available. Conflict resolution: last-writer-wins on the client; server timestamps win on download. Optimistic UI from slice 03 stays — the queue makes optimism *durable*. After this slice, going to airplane mode, logging 3 habits, killing the app, returning network → all 3 logs appear on the server within 2 seconds.

## 2. Pre-conditions

- [ ] Slice 03 done — VMs use HabitsService with optimistic toggle
- [ ] Slice 04 done OR live demo of streak computation works — needed so client can compute streaks consistently for offline detail screens

## 3. Files to create / modify

### Create
- `ios/HabitTracker/Core/Persistence/PersistenceStack.swift` — SwiftData `ModelContainer`; uses App Group container path (so widget can read the same store later)
- `ios/HabitTracker/Core/Persistence/PersistedHabit.swift` — `@Model` mirror of `Habit` + `serverUpdatedAt`, `pendingDeletion: Bool`
- `ios/HabitTracker/Core/Persistence/PersistedHabitLog.swift` — `@Model` mirror + `pendingSync: Bool`, `clientCreatedAt`
- `ios/HabitTracker/Core/Persistence/WriteOp.swift` — `@Model` enum-style: `.logHabit(habitID, date, note)`, `.unlogHabit(habitID, date)`, `.createHabit(payload)`, `.updateHabit(id, payload)`, `.deleteHabit(id)` — with `attempts`, `lastError`, `createdAt`
- `ios/HabitTracker/Core/Persistence/WriteQueue.swift` — actor; `enqueue(_:)`, `next() -> WriteOp?`, `markSucceeded(_)`, `markFailed(_, error)`
- `ios/HabitTracker/Core/Persistence/SyncEngine.swift` — actor; observes `WriteQueue` + `NWPathMonitor`; processes queue on connectivity; full pull on app foreground (delta by `updated_at`)
- `ios/HabitTracker/Core/Persistence/HabitRepository.swift` — facade replacing direct `HabitsService` calls in VMs: `todayHabits()`, `toggle(habit:on:)`, etc.; reads from SwiftData, writes to queue
- `ios/HabitTracker/Core/Services/Reachability.swift` — wrapper over `NWPathMonitor`
- `ios/HabitTracker/Core/Services/StreakComputer.swift` — Swift port of backend `schedule.py` + `streak_service.py`, used for offline streak display

### Modify
- `Features/Today/TodayViewModel.swift` — call `HabitRepository.todayHabits()` instead of `HabitsService.list()`; toggle calls repo
- `Features/HabitDetail/HabitDetailViewModel.swift` — read from repo; show "syncing…" badge if pending writes for this habit
- `Features/CreateEdit/*ViewModel.swift` — write through repo
- `HabitTrackerApp.swift` — instantiate `PersistenceStack`, `WriteQueue`, `SyncEngine`; start sync on launch + foreground
- `Features/Today/TodayView.swift` — small "offline" or "syncing N…" banner pinned bottom

### Tests
- `ios/HabitTrackerTests/PersistenceStackTests.swift` — container loads, schema migrates lightweight
- `ios/HabitTrackerTests/WriteQueueTests.swift` — FIFO order, persistence, retry semantics
- `ios/HabitTrackerTests/SyncEngineTests.swift` — processes queue, handles 5xx with backoff, full pull merges by `updated_at`
- `ios/HabitTrackerTests/HabitRepositoryTests.swift` — read-through, write-queue routing, optimistic visibility
- `ios/HabitTrackerTests/StreakComputerTests.swift` — port of backend tests; same expected values

### Backend (small additive)
- `backend/app/routers/habits.py` — ensure responses include `updated_at` (likely already do via TimestampMixin); add `?since=<iso>` filter on `GET /habits/` for delta sync
- `backend/tests/routers/test_habits_delta.py` — `test_list_since_returns_only_newer`

---

## 4. Tasks

### Task 5.1 — PersistenceStack + models + tests

**Description:** SwiftData container in App Group; `@Model` types mirroring server.

**Acceptance:**
- [ ] App Group entitlement added: `group.com.armandointeligencia.HabitTracker`
- [ ] `ModelContainer` created with `.appGroup(...)` URL
- [ ] `PersistedHabit`, `PersistedHabitLog`, `WriteOp` defined with proper relationships
- [ ] Lightweight migration scaffolding present (schema versioned)
- [ ] `PersistenceStackTests` GREEN

**Verify:** `⌘U`; reinstall app → cold launch creates DB; no crashes.

**Files:** `Core/Persistence/PersistenceStack.swift`, `PersistedHabit.swift`, `PersistedHabitLog.swift`, `WriteOp.swift`, `HabitTrackerTests/PersistenceStackTests.swift`, `ios/HabitTracker/HabitTracker.entitlements` (App Group), `ios/project.yml` (entitlement reference)

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`, `source-driven-development` (SwiftData docs), `test-driven-development`

---

### Task 5.2 — WriteQueue + tests

**Description:** Actor-isolated FIFO queue persisted in SwiftData.

**Acceptance:**
- [ ] `WriteQueue` is an `actor`
- [ ] Enqueue → durable; survives app kill
- [ ] FIFO ordering preserved
- [ ] Retry counter increments on failure; capped at 5; then surfaced to user as "needs your attention"
- [ ] Tests: enqueue/dequeue, persistence across stack restart, retry semantics, max-retry behavior

**Verify:** `⌘U`; force-kill simulator app between writes; relaunch → queue still has them.

**Files:** `Core/Persistence/WriteQueue.swift`, `HabitTrackerTests/WriteQueueTests.swift`

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development`

---

### Task 5.3 — Reachability + SyncEngine + tests

**Description:** Network monitor + queue processor with backoff. Full pull on foreground using `?since`.

**Acceptance:**
- [ ] `NWPathMonitor` exposed via `@Observable Reachability` actor; `isOnline: Bool`
- [ ] `SyncEngine.start()` runs on launch + on `Reachability` flip + on app `.didBecomeActive`
- [ ] Processes queue serially: pop → execute via `HabitsService` → on success, mark; on transient failure (network/5xx), exponential backoff 2/4/8/16/32s then leave in queue for next trigger
- [ ] Full pull: `GET /habits/?since=<lastSync>` → upsert into SwiftData, deletes pruned by tombstone
- [ ] Conflict policy: server `updated_at` newer → server wins; otherwise client write retried
- [ ] All `SyncEngineTests` GREEN

**Verify:** Live: airplane mode → log 3 habits → enable network → server records appear in <2s.

**Files:** `Core/Services/Reachability.swift`, `Core/Persistence/SyncEngine.swift`, `HabitTrackerTests/SyncEngineTests.swift`, `backend/app/routers/habits.py` (`?since` filter), `backend/tests/routers/test_habits_delta.py`

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development`, `source-driven-development` (Network framework, NWPathMonitor)

---

### Task 5.4 — HabitRepository facade + rewire VMs

**Description:** Thin layer in front of SwiftData + WriteQueue + HabitsService. VMs no longer call HabitsService directly; they call HabitRepository.

**Acceptance:**
- [ ] All VMs from slice 03 now talk only to `HabitRepository`
- [ ] `todayHabits()` returns from cache instantly; triggers background refresh
- [ ] `toggle(habit:on:)` → optimistic SwiftData mutation + WriteOp enqueue
- [ ] No view code changes
- [ ] `HabitRepositoryTests` GREEN

**Verify:** Live: airplane mode → toggle 3 habits → UI reflects → kill app → relaunch (still offline) → state persisted → enable network → server catches up.

**Files:** `Core/Persistence/HabitRepository.swift`, `Features/Today/TodayViewModel.swift`, `Features/HabitDetail/HabitDetailViewModel.swift`, `Features/CreateEdit/*ViewModel.swift`, `HabitTrackerTests/HabitRepositoryTests.swift`

**Skills:** `swift-actor-persistence`, `swiftui-patterns`, `test-driven-development`

---

### Task 5.5 — StreakComputer (Swift port) + tests

**Description:** Port `schedule.py` + streak logic from slice 04 to Swift so offline detail view shows correct streaks.

**Acceptance:**
- [ ] `StreakComputer.current(for habit, logs:)` matches backend output for all test cases
- [ ] `StreakComputer.longest(for habit, logs:)` matches
- [ ] Tests are a parallel of `test_streak_service.py` cases
- [ ] All GREEN
- [ ] HabitDetailView uses `StreakComputer` when offline; uses server values when online

**Verify:** Side-by-side: detail screen offline shows same streak as detail screen online (after sync).

**Files:** `Core/Services/StreakComputer.swift`, `HabitTrackerTests/StreakComputerTests.swift`

**Skills:** `test-driven-development`, `code-simplification`, `swift-concurrency-6-2`

---

### Task 5.6 — Offline UX banner

**Description:** Small visual cue when offline or pending writes.

**Acceptance:**
- [ ] When `Reachability.isOnline == false`, banner pinned to bottom of TodayView: "Offline — N changes will sync"
- [ ] When N pending writes (online or offline), banner shows "Syncing N…"; auto-dismisses on empty
- [ ] Themed via current AppTheme

**Verify:** Live; toggle airplane mode several times.

**Files:** `Features/Today/TodayView.swift`, `Features/Today/SyncBanner.swift`

**Skills:** `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design`

---

## 5. Test plan (RED → GREEN order)

| File | Cases | Phase |
|---|---|---|
| `PersistenceStackTests.swift` | `testContainerLoads`, `testAppGroupURL`, `testReinstallStartsClean` | 5.1 |
| `WriteQueueTests.swift` | `testEnqueueDequeueFIFO`, `testPersistsAcrossRestart`, `testRetryIncrementsAttempts`, `testMaxRetriesSurfacesError`, `testMarkSucceededRemoves` | 5.2 |
| `SyncEngineTests.swift` | `testProcessesQueueWhenOnline`, `testWaitsForReachabilityWhenOffline`, `testExponentialBackoffOnTransientFailure`, `testFullPullDeltaMergesUpdatedAt`, `testServerWinsOnConflict`, `testTombstoneDeletes` | 5.3 |
| `test_habits_delta.py` (backend) | `test_list_since_returns_only_newer`, `test_list_since_empty_returns_all`, `test_list_since_respects_user_scope` | 5.3 |
| `HabitRepositoryTests.swift` | `testTodayReadsFromCacheFirst`, `testToggleOptimisticAndQueues`, `testCreateAppearsInCacheImmediately`, `testDeleteIsTombstoned` | 5.4 |
| `StreakComputerTests.swift` | mirror of all `test_streak_service.py` cases | 5.5 |

---

## 6. Skills mapping

| Task | Primary | Secondary |
|---|---|---|
| 5.1 | `swift-actor-persistence`, `swift-concurrency-6-2`, `source-driven-development`, `test-driven-development` | — |
| 5.2 | `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development` | — |
| 5.3 | `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development`, `source-driven-development` | `api-and-interface-design` (since param) |
| 5.4 | `swift-actor-persistence`, `swiftui-patterns`, `test-driven-development` | — |
| 5.5 | `test-driven-development`, `code-simplification`, `swift-concurrency-6-2` | — |
| 5.6 | `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design` | — |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| SwiftData schema migration breaks user data on app update | High | Versioned schemas; lightweight migration plan; tested in CI cold-install + upgrade simulator runs |
| WriteOp enum evolution requires migration | Med | Use stable string `kind` discriminator + JSON `payload` blob in `@Model` (avoids enum-in-Model fragility) |
| Concurrent toggle taps race with sync | Med | All writes go through `WriteQueue` actor; serialization built-in |
| Tombstone deletes get re-created by stale server pull | Med | Soft-delete with `deleted_at` on backend; pull respects it (backend returns deleted=true tombstones) → backend change in this slice |
| Network blip during full pull leaves partial state | Low | Pull is wrapped in a single SwiftData transaction; rollback on error |
| Battery drain from constant `NWPathMonitor` | Low | iOS handles efficiently; document trade-off |

**Backend tombstone addition:** add `deleted_at` to `habits` table (Slice 04 or here as small migration). Decision: add in this slice as Task 5.7 if not done.

---

### Task 5.7 — Backend soft-delete tombstones (added per risk register)

**Description:** Convert habit deletion from hard-delete to soft-delete. List endpoint with `?since=` returns deleted-tombstones so iOS can prune local cache.

**Acceptance:**
- [ ] `habits.deleted_at` column added (nullable timestamp)
- [ ] DELETE endpoint sets `deleted_at = now()` instead of removing
- [ ] List endpoint excludes deleted by default; with `?include_deleted=true` returns tombstones (used by `?since` flow)
- [ ] Cascade behavior reviewed: `habit_logs` not deleted on habit soft-delete, but excluded from queries via join
- [ ] Migration written and tested
- [ ] Tests cover all three behaviors

**Files:** `backend/app/models/habit.py`, `backend/alembic/versions/<auto>_soft_delete_habits.py`, `backend/app/routers/habits.py`, `backend/app/services/habit_service.py`, `backend/tests/routers/test_habits_softdelete.py`

**Skills:** `database-migrations`, `api-and-interface-design`, `test-driven-development`, `deprecation-and-migration`

---

## 8. Definition of done

- [ ] All test files in §5 GREEN (iOS + backend)
- [ ] Live offline demo: airplane mode → 3 toggles + 1 create → app kill → relaunch → enable network → server catches up in <2s
- [ ] Detail view streak values match server when reconnected
- [ ] Banner UX clear on offline / syncing states
- [ ] No SwiftData crash on cold install or app upgrade
- [ ] App Group entitlement signed and working
- [ ] Slice committed: `feat(ios): SwiftData cache + write queue + sync engine; feat(backend): soft-delete + delta pull`
- [ ] User reviewed; CHECKPOINT C reached (RRULE + offline both green)

## 9. Estimated session count

**4 sessions:**
- Session 1: Tasks 5.1 + 5.7 (persistence stack + backend tombstones)
- Session 2: Task 5.2 (WriteQueue)
- Session 3: Task 5.3 (SyncEngine — biggest)
- Session 4: Tasks 5.4 + 5.5 + 5.6 (repo + StreakComputer + banner)

## 10. What unblocks the next slice

- Widget (slice 07) reads SwiftData via App Group — store now exists in shared container
- Notifications (slice 06) can read `PersistedHabit.reminderTime` from local cache without backend
- Live Activity (slice 08) can update from local SwiftData while running
- Offline-capable foundation lets next 3 slices focus on iOS-native features without worrying about network

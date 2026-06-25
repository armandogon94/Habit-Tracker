# Slice 07 — iOS Home Screen widget (WidgetKit, App Group)

> **Implements:** SPEC §1 "Home Screen widget showing today's habits", §9 Q2 (hourly + relevance refresh)
> **Status:** READY (depends on Slice 05 — App Group container; ideally after Slice 06 too for completeness)
> **Estimated sessions:** 2
> **Unblocks:** None directly

---

## 1. Objective

Add a WidgetKit extension target that shows today's habits on the Home Screen and Lock Screen. Two widget sizes: **Medium** (3–5 habits with checkable circles) and **Small** (single most-relevant habit + streak). Uses the **App Group SwiftData store** from slice 05 — the widget is read-only on the data; tapping a habit's check circle uses `AppIntent` to log via the same `WriteQueue` used by the main app, so logs flow to the server through normal sync. Refresh cadence: hourly background timeline + relevance-based bumps when reminder times approach.

## 2. Pre-conditions

- [ ] Slice 05 done — App Group container with SwiftData store exists
- [ ] Slice 06 done (recommended) — `reminder_time` exists for relevance scoring

## 3. Files to create / modify

### New target
- Add `HabitTrackerWidget` target to `ios/project.yml`:
  - Type: `app-extension`
  - Bundle id: `com.armandointeligencia.HabitTracker.Widget`
  - Deployment target: 26.0
  - Entitlements: same App Group `group.com.armandointeligencia.HabitTracker`
  - Sources: `ios/HabitTrackerWidget/`

### Create
- `ios/HabitTrackerWidget/HabitTrackerWidgetBundle.swift` — `@main` widget bundle
- `ios/HabitTrackerWidget/TodayWidget.swift` — Widget definition; supports `.systemSmall`, `.systemMedium`, `.accessoryRectangular` (lock screen)
- `ios/HabitTrackerWidget/TodayTimelineProvider.swift` — provides `TimelineEntry`s every hour + on relevance
- `ios/HabitTrackerWidget/TodayWidgetEntry.swift` — entry model: `date`, `habits: [WidgetHabit]`
- `ios/HabitTrackerWidget/WidgetHabit.swift` — minimal display model for widget
- `ios/HabitTrackerWidget/Views/MediumWidgetView.swift`
- `ios/HabitTrackerWidget/Views/SmallWidgetView.swift`
- `ios/HabitTrackerWidget/Views/AccessoryRectangularView.swift`
- `ios/HabitTrackerWidget/Intents/LogHabitIntent.swift` — `AppIntent` to mark a habit done from widget tap
- `ios/HabitTrackerWidget/WidgetTheme.swift` — minimal theme tokens (widgets can't easily share full theme with main app; mirror Liquid Glass + Health Cards essentials, theme picked via App Group UserDefaults)
- `ios/HabitTracker/Core/Persistence/SharedStoreReader.swift` — main-app-side mirror used by both targets to read PersistedHabit consistently

### Modify
- `ios/HabitTracker/HabitTracker.entitlements` — confirm App Group + UserDefaults suite
- `ios/HabitTracker/Core/Persistence/PersistenceStack.swift` — expose convenience init for widget extension
- `ios/HabitTracker/Core/Theme/ThemeStore.swift` — also write current theme to App Group UserDefaults so widget reads it

### Tests
- `ios/HabitTrackerTests/SharedStoreReaderTests.swift` — main app + widget read same store
- `ios/HabitTrackerWidgetTests/TodayTimelineProviderTests.swift` — entries generated correctly
- `ios/HabitTrackerWidgetTests/LogHabitIntentTests.swift` — intent enqueues WriteOp

---

## 4. Tasks

### Task 7.1 — Widget target scaffold + smoke

**Description:** Add target via XcodeGen, get an empty widget visible on simulator Home Screen.

**Acceptance:**
- [ ] `ios/project.yml` defines widget target with shared App Group entitlement
- [ ] `xcodegen` regenerates project successfully
- [ ] `⌘R` builds widget; long-press Home Screen on simulator → "Habit Tracker" appears in widget gallery
- [ ] Empty placeholder widget renders

**Verify:** Live in simulator.

**Files:** `ios/project.yml`, `ios/HabitTrackerWidget/HabitTrackerWidgetBundle.swift`, `ios/HabitTrackerWidget/TodayWidget.swift` (placeholder), `ios/HabitTracker.entitlements`

**Skills:** `swiftui-patterns`, `source-driven-development` (WidgetKit docs), `swift-concurrency-6-2`

---

### Task 7.2 — SharedStoreReader + theme propagation

**Description:** Both main app and widget read the same SwiftData store via App Group container path. ThemeStore writes current theme id to App Group UserDefaults so widget can pick correct colors.

**Acceptance:**
- [ ] `SharedStoreReader.todayHabits()` returns same data when called from both targets
- [ ] App Group UserDefaults holds `selected_theme_id`
- [ ] WidgetTheme reads it on every timeline build
- [ ] Tests cover read consistency
- [ ] Tests cover theme key fallback (default = liquidGlass)

**Verify:** `⌘U`; manual: switch theme in app → wait for widget refresh → widget recolors.

**Files:** `Core/Persistence/SharedStoreReader.swift`, `Core/Theme/ThemeStore.swift`, `HabitTrackerWidget/WidgetTheme.swift`, `HabitTrackerTests/SharedStoreReaderTests.swift`

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development`

---

### Task 7.3 — TimelineProvider + entries

**Description:** Provide entries hourly + when reminder times approach.

**Acceptance:**
- [ ] `placeholder` returns mocked snapshot
- [ ] `snapshot` reads from SharedStoreReader
- [ ] `timeline` returns next 24 entries, 1/hour, plus extra entries 5 minutes before each habit's reminder_time
- [ ] Reload policy: `.atEnd` with relevance signals
- [ ] Tests verify entry count + timing

**Verify:** Build + add widget; observe entry refresh in Console.app logs.

**Files:** `HabitTrackerWidget/TodayTimelineProvider.swift`, `HabitTrackerWidget/TodayWidgetEntry.swift`, `HabitTrackerWidget/WidgetHabit.swift`, `HabitTrackerWidgetTests/TodayTimelineProviderTests.swift`

**Skills:** `swiftui-patterns`, `source-driven-development`, `test-driven-development`, `performance-optimization` (timeline budget)

---

### Task 7.4 — Widget views (Medium, Small, Lock Screen)

**Description:** Three sizes, both themes.

**Acceptance:**
- [ ] Medium: up to 5 habit rows, each with check button (AppIntent), name truncated, color dot
- [ ] Small: 1 habit (highest unfinished priority by reminder time), big check button, streak under name
- [ ] Lock-screen accessoryRectangular: "X of Y done" + small bar gauge
- [ ] Both themes render via WidgetTheme
- [ ] No personally identifiable info shown in lock screen if user disables sensitive content (handle `.privacySensitive`)

**Verify:** Add all 3 sizes to Home Screen + Lock Screen; visual review.

**Files:** `HabitTrackerWidget/Views/MediumWidgetView.swift`, `SmallWidgetView.swift`, `AccessoryRectangularView.swift`

**Skills:** `swiftui-patterns`, `liquid-glass-design`, `ios-hig-design`, `frontend-ui-engineering`

---

### Task 7.5 — LogHabitIntent (AppIntent → WriteQueue)

**Description:** Tap on widget check-button enqueues a write through the SAME WriteQueue used by main app. Widget DOES NOT call API directly.

**Acceptance:**
- [ ] `LogHabitIntent` is `AppIntent` with `habitID: String` parameter
- [ ] `perform()` opens shared WriteQueue, enqueues `.logHabit(habitID, today)`
- [ ] Widget reloads timeline immediately
- [ ] Main app SyncEngine processes it on next foreground/connectivity event
- [ ] Tests verify enqueue happens

**Verify:** Live: tap check on widget → tap done in widget visually + later open app → habit shows logged.

**Files:** `HabitTrackerWidget/Intents/LogHabitIntent.swift`, `HabitTrackerWidgetTests/LogHabitIntentTests.swift`

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`, `swiftui-patterns`, `test-driven-development`, `source-driven-development` (App Intents docs)

---

## 5. Test plan

| File | Cases | Phase |
|---|---|---|
| `SharedStoreReaderTests.swift` | `testReadsHabitsFromAppGroupContainer`, `testReadConsistencyAfterMainAppWrite` | 7.2 |
| `TodayTimelineProviderTests.swift` | `testPlaceholderShape`, `testSnapshotReadsStore`, `testTimelineHasHourlyEntries`, `testTimelineAddsEntryBeforeReminder`, `testEmptyHabitsGracefullyHandled` | 7.3 |
| `LogHabitIntentTests.swift` | `testPerformEnqueuesWriteOp`, `testInvalidHabitIDFailsGracefully` | 7.5 |

---

## 6. Skills mapping

| Task | Primary | Secondary |
|---|---|---|
| 7.1 | `swiftui-patterns`, `source-driven-development`, `swift-concurrency-6-2` | — |
| 7.2 | `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development` | — |
| 7.3 | `swiftui-patterns`, `source-driven-development`, `test-driven-development`, `performance-optimization` | — |
| 7.4 | `swiftui-patterns`, `liquid-glass-design`, `ios-hig-design`, `frontend-ui-engineering` | — |
| 7.5 | `swift-actor-persistence`, `swift-concurrency-6-2`, `swiftui-patterns`, `test-driven-development` | `source-driven-development` |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Widget timeline budget exceeded → iOS throttles refresh | Med | Cap at 24 hourly + ~6 reminder entries = ~30/timeline; well within budget |
| Widget data stale until next refresh | Med | Manual refresh on AppIntent perform; reload from main-app side after sync via `WidgetCenter.reloadTimelines` |
| App Group read-write race between main and widget | Med | Widget is READ-ONLY on store; only main-app SyncEngine writes via WriteQueue actor |
| Theme propagation lag → widget shows wrong colors briefly | Low | Acceptable; widget refreshes within minutes |
| Widget extension memory limit (30 MB) | Low | Keep view code lean; no large images |
| Lock-screen privacy when device locked | Med | `.privacySensitive` modifier on habit names; respects user system setting |

---

## 8. Definition of done

- [ ] All test files in §5 GREEN
- [ ] Three widget sizes installable from gallery
- [ ] Tap-to-log on widget enqueues write; appears in main app + on server
- [ ] Theme switch in main app reflects in widget on next refresh
- [ ] Lock-screen widget renders, respects sensitive-content setting
- [ ] No crashes when app uninstalled then widget left on screen briefly
- [ ] Slice committed: `feat(ios): home + lock screen widgets, App Intents log-from-widget`

## 9. Estimated session count

**2 sessions:**
- Session 1: Tasks 7.1, 7.2, 7.3 (target + reader + timeline)
- Session 2: Tasks 7.4 + 7.5 (views + AppIntent)

## 10. What unblocks the next slice

- Widget proves App Group + shared SwiftData store works → slice 08 Live Activity uses similar shared-state pattern
- WidgetCenter reload pattern reusable in slice 08 for activity updates

# Slice 00 — iOS scaffold + Mockup (mock data, both themes)

> **Implements:** SPEC §1 "Mockup milestone", §2 iOS stack, §4 iOS structure, §8 mockup criteria, §9 Q3 (onboarding)
> **Status:** READY
> **Estimated sessions:** 4–6
> **Unblocks:** Slice 01 (no dependency, but mockup user sign-off comes first)

---

## 1. Objective

Stand up a runnable iOS 26 SwiftUI app at `02-Habit-Tracker/ios/HabitTracker/` that mirrors the proven structure of `04-Finance-Tracker/ios/`. The app uses **only `MockData`** — zero networking, zero backend dependency. Every main screen is implemented with both **Liquid Glass** and **Health Cards** themes, switchable live via a `DesignPlaygroundView` and a Settings → Theme toggle. The user can install on simulator or device, navigate every screen, and sign off on the visual direction before any API code is written. Also verifies that Apple Developer signing works end-to-end (dry-run TestFlight archive at end of slice) so we don't discover signing problems in slice 11.

## 2. Pre-conditions

- [ ] `xcodegen` installed: `brew install xcodegen`
- [ ] Xcode 16+ installed with iOS 26 SDK
- [ ] Apple Developer account active (for signing dry-run at end)
- [ ] User has reviewed SPEC.md §1 mockup criteria

## 3. Files to create

### Project root
- `ios/project.yml` — XcodeGen config (model on 04-Finance-Tracker/ios/project.yml exactly; rename app to HabitTracker, bundle id `com.armandointeligencia.HabitTracker`, deployment 26.0, Swift 6.0)
- `ios/.gitignore` — exclude `*.xcodeproj/xcuserdata`, `*.xcworkspace/xcuserdata`, `DerivedData`, `.build`, `Pods`

### App entry
- `ios/HabitTracker/HabitTrackerApp.swift` — `@main` app, injects `ThemeStore` env
- `ios/HabitTracker/RootView.swift` — TabView with Today / Analytics / Settings; gated by mock auth toggle

### Theme system (PORT FROM 04-Finance-Tracker)
- `ios/HabitTracker/Core/Theme/AppTheme.swift` — protocol identical to 04 (rename `ThemeID` cases to `liquidGlass`, `healthCards`)
- `ios/HabitTracker/Core/Theme/LiquidGlassTheme.swift` — copy from 04, tweak categoryColors for habit-tracker palette (greens for "done", reds for "missed", neutral grays)
- `ios/HabitTracker/Core/Theme/HealthCardsTheme.swift` — copy from 04 PlaceholderThemes.swift D5 section
- `ios/HabitTracker/Core/Theme/ThemeStore.swift` — `@Observable @MainActor`; persists choice in `UserDefaults`; reads on app launch
- `ios/HabitTracker/Core/Theme/ThemedCard.swift` — reusable card wrapper using `cardBackground()` + `radii.card` + `spacing.lg` padding
- `ios/HabitTracker/Core/Theme/ThemedBackdrops.swift` — reusable hero gradient backdrop
- `ios/HabitTracker/Core/Theme/CategoryIcon.swift` — habit icon (SF Symbols mapped per habit color/name) — adapted from 04

### Mock data
- `ios/HabitTracker/Core/MockData/MockData.swift` — 6 habits (Meditate, Read, Exercise, Drink Water, Journal, Plan Tomorrow) with realistic streak histories spanning 60 days, varying RRULEs (daily, weekdays-only, weekly MWF)
- `ios/HabitTracker/Core/MockData/MockUser.swift` — Armando, timezone, role: user

### Domain models
- `ios/HabitTracker/Models/Models.swift` — `Habit`, `HabitLog`, `User`, `Streak` value types matching backend DTOs (Codable, Identifiable, Sendable)
- `ios/HabitTracker/Models/RRULE.swift` — minimal parser for the 3 RRULEs we use (daily, weekdays, weekly+BYDAY) — full lib in slice 03

### Features (mock-data versions)
- `ios/HabitTracker/Features/Auth/LoginView.swift` — visual only, "Sign in" button skips into the app (mock auth)
- `ios/HabitTracker/Features/Auth/RegisterView.swift` — visual only
- `ios/HabitTracker/Features/Onboarding/FirstRunSheet.swift` — single screen: notif permission CTA + theme pick (decision Q3)
- `ios/HabitTracker/Features/Today/TodayView.swift` — list of today's habits, hero "X of Y done", themed cards, FAB to add
- `ios/HabitTracker/Features/Today/HabitRow.swift` — checkable row with streak badge
- `ios/HabitTracker/Features/Today/QuickLogSheet.swift` — confirm completion with optional note
- `ios/HabitTracker/Features/HabitDetail/HabitDetailView.swift` — stats hero + heatmap + weekly chart + log history
- `ios/HabitTracker/Features/HabitDetail/HeatmapCanvas.swift` — Canvas-based 7×N grid, color intensity = completion
- `ios/HabitTracker/Features/HabitDetail/WeeklyChart.swift` — Swift Charts BarMark
- `ios/HabitTracker/Features/CreateEdit/CreateHabitSheet.swift` — name, color, RRULE picker (3 presets), reminder time
- `ios/HabitTracker/Features/CreateEdit/EditHabitSheet.swift` — same form, prefilled
- `ios/HabitTracker/Features/CreateEdit/RRULEPicker.swift` — segmented control: Daily / Weekdays / Custom (M-F-S checkboxes)
- `ios/HabitTracker/Features/Analytics/AnalyticsView.swift` — overall completion rate, longest streaks, Swift Charts donut by habit
- `ios/HabitTracker/Features/Settings/SettingsView.swift` — theme toggle, language toggle (placeholder), notif settings, sign-out
- `ios/HabitTracker/Features/Settings/DesignPlaygroundView.swift` — side-by-side theme preview of 6 key screens (port from 04)

### Resources
- `ios/HabitTracker/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json` — placeholder app icon
- `ios/HabitTracker/Resources/Assets.xcassets/AccentColor.colorset/Contents.json`

### Tests (RED first)
- `ios/HabitTrackerTests/ThemeTokenTests.swift` — both themes provide all required tokens
- `ios/HabitTrackerTests/MockDataTests.swift` — mock data is internally consistent (no orphaned logs)
- `ios/HabitTrackerTests/RRULEParserTests.swift` — 3 supported patterns parse to expected schedule
- `ios/HabitTrackerTests/ModelCodableTests.swift` — Habit, HabitLog round-trip JSON

### Docs
- `ios/docs/mockup-screenshots/` — directory; populate at end of slice with PNG of every screen × 2 themes = ~20 images
- `ios/docs/SIGNING.md` — captured signing setup notes for slice 11

---

## 4. Tasks

### Task 0.1 — XcodeGen scaffold + project opens

**Description:** Get a clean buildable empty Xcode project that opens, has both targets, and runs an empty `WindowGroup`.

**Acceptance:**
- [ ] `cd ios && xcodegen` succeeds with no warnings
- [ ] `open ios/HabitTracker.xcodeproj` opens Xcode
- [ ] `⌘R` builds and runs the empty app on iPhone 16 Pro simulator (iOS 26)
- [ ] Bundle id is `com.armandointeligencia.HabitTracker`, display name "Habit Tracker"
- [ ] `HabitTrackerTests` target exists, `⌘U` runs zero tests successfully

**Verify:**
```bash
cd ios && xcodegen generate
xcodebuild -project HabitTracker.xcodeproj -scheme HabitTracker -destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=26.0' build
```

**Files:** `ios/project.yml`, `ios/HabitTracker/HabitTrackerApp.swift`, `ios/HabitTracker/RootView.swift`, `ios/HabitTrackerTests/SmokeTest.swift`, `ios/.gitignore`

**Skills:** `swiftui-patterns`, `source-driven-development` (consult Apple docs for iOS 26 specifics), `git-workflow-and-versioning`

---

### Task 0.2 — Theme protocol + two concrete themes + ThemeStore

**Description:** Port `AppTheme` protocol and both themes from 04-Finance-Tracker. Theme persists in UserDefaults. Inject as environment.

**Acceptance:**
- [ ] `AppTheme` protocol matches 04's surface (all tokens present)
- [ ] `LiquidGlassTheme` and `HealthCardsTheme` both implement protocol
- [ ] `ThemeStore` exposes `current: any AppTheme`, `setTheme(ThemeID)`, persists choice
- [ ] Tests in `ThemeTokenTests` pass — RED before, GREEN after

**Verify:** `⌘U` green; manually flip theme in a Preview.

**Files:** `Core/Theme/AppTheme.swift`, `Core/Theme/LiquidGlassTheme.swift`, `Core/Theme/HealthCardsTheme.swift`, `Core/Theme/ThemeStore.swift`, `HabitTrackerTests/ThemeTokenTests.swift`

**Skills:** `liquid-glass-design`, `swiftui-patterns`, `swift-concurrency-6-2` (`@MainActor` on the store), `test-driven-development`

---

### Task 0.3 — ThemedCard + ThemedBackdrops + CategoryIcon helpers

**Description:** Reusable view modifiers/wrappers so every screen consistently uses theme tokens.

**Acceptance:**
- [ ] `ThemedCard { … }` produces a card with theme background, radius, padding
- [ ] `ThemedBackdrop()` provides hero gradient
- [ ] `CategoryIcon(for: habit)` returns SF Symbol view in habit's color
- [ ] Renders in both themes via Preview

**Verify:** Preview screenshots in both themes show consistent styling.

**Files:** `Core/Theme/ThemedCard.swift`, `Core/Theme/ThemedBackdrops.swift`, `Core/Theme/CategoryIcon.swift`

**Skills:** `swiftui-patterns`, `liquid-glass-design`

---

### Task 0.4 — Domain models + RRULE parser + tests

**Description:** Codable domain types plus a small RRULE evaluator for the 3 patterns we use.

**Acceptance:**
- [ ] `Habit`, `HabitLog`, `User` are `Codable, Identifiable, Sendable, Hashable`
- [ ] `RRULE.scheduledDates(in:)` returns correct dates for `FREQ=DAILY`, `FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR`, `FREQ=WEEKLY;BYDAY=MO,WE,FR`
- [ ] `RRULEParserTests` — 9+ cases (3 RRULEs × 3 sample weeks) — RED then GREEN
- [ ] `ModelCodableTests` — round-trip with backend's snake_case JSON convention via `JSONDecoder.keyDecodingStrategy = .convertFromSnakeCase`

**Verify:** `⌘U` green.

**Files:** `Models/Models.swift`, `Models/RRULE.swift`, `HabitTrackerTests/RRULEParserTests.swift`, `HabitTrackerTests/ModelCodableTests.swift`

**Skills:** `test-driven-development`, `swift-concurrency-6-2`, `source-driven-development` (RFC 5545 reference)

---

### Task 0.5 — MockData

**Description:** Realistic mock data: 6 habits with 60 days of varied logs to make charts and heatmaps look alive.

**Acceptance:**
- [ ] `MockData.habits` returns 6 distinct habits, varied RRULEs and colors
- [ ] `MockData.logs(for:)` returns ~30–55 logs per habit over last 60 days, varying density
- [ ] `MockDataTests` confirms no log dates exceed today, all habit IDs match
- [ ] Each habit has a believable streak (one with 23-day current streak, one missed yesterday, one weekday-only)

**Verify:** `⌘U` green; visual inspection in Preview.

**Files:** `Core/MockData/MockData.swift`, `Core/MockData/MockUser.swift`, `HabitTrackerTests/MockDataTests.swift`

**Skills:** `test-driven-development`

---

### Task 0.6 — TodayView + HabitRow + QuickLogSheet (mock)

**Description:** Home tab. Shows today's scheduled habits per RRULE; tapping a row toggles completion locally (in-memory only).

**Acceptance:**
- [ ] Hero "X of Y done today" updates as you tap rows
- [ ] Rows show name, streak badge, color dot
- [ ] Toggle is animated, haptic feedback (UIImpactFeedbackGenerator)
- [ ] Long-press opens QuickLogSheet with note field
- [ ] Renders correctly in both themes (verify with `.preferredColorScheme` previews)

**Verify:** Live in simulator; toggle 3 habits, hero count matches.

**Files:** `Features/Today/TodayView.swift`, `Features/Today/HabitRow.swift`, `Features/Today/QuickLogSheet.swift`, `RootView.swift` (wire tab)

**Skills:** `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design`, `frontend-ui-engineering`

---

### Task 0.7 — HabitDetailView + HeatmapCanvas + WeeklyChart

**Description:** Tap a habit → detail screen with hero stats, custom Canvas heatmap, Swift Charts weekly bar chart, log history list.

**Acceptance:**
- [ ] Hero shows: current streak, longest streak, total completions, completion rate
- [ ] Heatmap is a 7-row × N-column grid (Canvas), color intensity from `surfaceSecondary` → `accent`, weekday labels on left
- [ ] WeeklyChart is `BarMark` per weekday, last 4 weeks aggregated
- [ ] Log history list (last 10 entries) at bottom
- [ ] Both themes look polished (review screenshots)

**Verify:** Live in simulator; check 3 different habits.

**Files:** `Features/HabitDetail/HabitDetailView.swift`, `Features/HabitDetail/HeatmapCanvas.swift`, `Features/HabitDetail/WeeklyChart.swift`

**Skills:** `swiftui-patterns`, `liquid-glass-design`, `ios-hig-design`, `source-driven-development` (Swift Charts docs)

---

### Task 0.8 — CreateHabitSheet + EditHabitSheet + RRULEPicker

**Description:** Form for creating and editing a habit. Mock-only: writes go to in-memory store.

**Acceptance:**
- [ ] Name, color picker, RRULE picker (Daily / Weekdays / Custom MTWTFSS), reminder time picker
- [ ] Validation: name required, length ≤100
- [ ] Save dismisses sheet and updates TodayView
- [ ] Edit sheet prefills from existing habit
- [ ] Both themes render cleanly

**Verify:** Create a habit, see it appear; edit it, see change.

**Files:** `Features/CreateEdit/CreateHabitSheet.swift`, `Features/CreateEdit/EditHabitSheet.swift`, `Features/CreateEdit/RRULEPicker.swift`

**Skills:** `swiftui-patterns`, `ios-hig-design`, `frontend-ui-engineering`

---

### Task 0.9 — AnalyticsView (mock data)

**Description:** Analytics tab. Overall completion rate, top habits by streak, Swift Charts donut by habit.

**Acceptance:**
- [ ] Cards: Total habits, Completion rate (30d), Longest streak, Logs total
- [ ] Donut chart of completion share per habit
- [ ] Renders in both themes

**Verify:** Live in simulator.

**Files:** `Features/Analytics/AnalyticsView.swift`

**Skills:** `swiftui-patterns`, `liquid-glass-design`, `frontend-ui-engineering`

---

### Task 0.10 — SettingsView + DesignPlaygroundView

**Description:** Settings tab with theme picker, language placeholder, notif toggle (UI only), sign-out (returns to LoginView mock). DesignPlaygroundView shows 6 screens side-by-side per theme — internal tool for design A/B.

**Acceptance:**
- [ ] Theme picker (segmented control) flips theme app-wide instantly
- [ ] DesignPlayground shows all 6 main screens at thumbnail size in both themes
- [ ] Settings is reachable from RootView tab
- [ ] Sign-out returns to LoginView (mock)

**Verify:** Tap theme button — entire app updates within 1 frame.

**Files:** `Features/Settings/SettingsView.swift`, `Features/Settings/DesignPlaygroundView.swift`

**Skills:** `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design`

---

### Task 0.11 — LoginView + RegisterView + FirstRunSheet (mock auth)

**Description:** Visual-only auth screens; "Sign in" button advances to RootView. FirstRunSheet appears on first launch (UserDefaults flag) with notif permission + theme pick.

**Acceptance:**
- [ ] LoginView: email + password fields, "Sign in" CTA, "Register" link
- [ ] RegisterView: email + password + confirm, "Create" CTA
- [ ] FirstRunSheet: shown only on first launch; theme pick + "Allow Notifications" CTA (calls `UNUserNotificationCenter.requestAuthorization`)
- [ ] After sign-in, RootView shows; sign-out returns here
- [ ] Both themes look identical-ish in spirit

**Verify:** Delete app from simulator, reinstall → first-run sheet appears once.

**Files:** `Features/Auth/LoginView.swift`, `Features/Auth/RegisterView.swift`, `Features/Onboarding/FirstRunSheet.swift`, `RootView.swift` (gate logic)

**Skills:** `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design`

---

### Task 0.12 — Mockup screenshot pass

**Description:** Take PNG screenshots of every main screen × 2 themes (~20 images), commit to `ios/docs/mockup-screenshots/`.

**Acceptance:**
- [ ] 10 screens captured: Login, Register, FirstRun, Today, HabitDetail, Create, Edit, Analytics, Settings, DesignPlayground
- [ ] Each in both themes (PNG, simulator-rendered, no status-bar UI overlap)
- [ ] All committed; user reviews in PR/diff

**Verify:** `ls ios/docs/mockup-screenshots/ | wc -l` ≥ 20.

**Files:** screenshots only (binary).

**Skills:** `ui-demo` (use Playwright/sim screenshot tooling)

---

### Task 0.13 — Signing dry-run (early-fail check)

**Description:** Before slice 11, prove signing works end-to-end. Configure Apple Developer team in Xcode, archive a build, upload to App Store Connect as an early TestFlight build candidate (don't distribute yet). If this breaks, we want to know NOW.

**Acceptance:**
- [ ] `DEVELOPMENT_TEAM` set in `ios/project.yml` (committed)
- [ ] `xcodebuild -archivePath build/HabitTracker.xcarchive archive` succeeds
- [ ] Archive uploads to App Store Connect (manual via Xcode Organizer is fine)
- [ ] Notes captured in `ios/docs/SIGNING.md`

**Verify:** App Store Connect shows a build under HabitTracker app record.

**Files:** `ios/project.yml`, `ios/docs/SIGNING.md`

**Skills:** `shipping-and-launch`, `documentation-and-adrs`

---

## 5. Test plan (RED → GREEN order)

| Test file | Cases | Phase |
|---|---|---|
| `SmokeTest.swift` | `testAppLaunches` | 0.1 |
| `ThemeTokenTests.swift` | `testLiquidGlassProvidesAllTokens`, `testHealthCardsProvidesAllTokens`, `testThemeStoreSwitchesAndPersists` | 0.2 |
| `RRULEParserTests.swift` | `testDailyEveryDay`, `testWeekdaysSkipsWeekends`, `testWeeklyMWFOnly`, +negative cases for unsupported patterns | 0.4 |
| `ModelCodableTests.swift` | `testHabitRoundTripJSON`, `testHabitLogRoundTripJSON`, `testSnakeCaseDecoding` | 0.4 |
| `MockDataTests.swift` | `testNoOrphanedLogs`, `testNoFutureLogDates`, `testEachHabitHasLogs` | 0.5 |

All RED before any view code, GREEN before slice closes.

---

## 6. Skills mapping (per task)

| Task | Primary skills | Optional/secondary |
|---|---|---|
| 0.1 | `swiftui-patterns`, `source-driven-development` | `git-workflow-and-versioning` |
| 0.2 | `liquid-glass-design`, `swiftui-patterns`, `swift-concurrency-6-2`, `test-driven-development` | — |
| 0.3 | `swiftui-patterns`, `liquid-glass-design` | — |
| 0.4 | `test-driven-development`, `swift-concurrency-6-2`, `source-driven-development` | — |
| 0.5 | `test-driven-development` | — |
| 0.6 | `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design`, `frontend-ui-engineering` | — |
| 0.7 | `swiftui-patterns`, `liquid-glass-design`, `ios-hig-design`, `source-driven-development` | — |
| 0.8 | `swiftui-patterns`, `ios-hig-design`, `frontend-ui-engineering` | — |
| 0.9 | `swiftui-patterns`, `liquid-glass-design` | — |
| 0.10 | `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design` | — |
| 0.11 | `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design` | — |
| 0.12 | `ui-demo` | — |
| 0.13 | `shipping-and-launch`, `documentation-and-adrs` | — |

Cross-cutting: `code-review-and-quality` at end of slice; `git-workflow-and-versioning` per commit.

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| iOS 26 SDK API change between betas | Med | Pin Xcode 16+; encapsulate iOS-26-specific calls in single file per feature |
| Liquid Glass material APIs differ from public docs | Med | Reference 04-Finance-Tracker's `LiquidGlassTheme` exactly; consult Apple HIG |
| Swift 6 strict concurrency complaints in helper code | Low | `@MainActor` view models, `Sendable` value types — already enforced in 04 |
| Signing setup blocks at end | High | Task 0.13 does dry-run early; if blocked, we have time to fix before slice 11 |
| Mockup approved but reality diverges later | Med | Screenshots committed, become visual contract for slices 02+ |
| Designer/user wants 3rd theme | Low | `AppTheme` protocol scales; defer to v2 |

---

## 8. Definition of done

- [ ] `xcodegen && open` produces a project that builds clean
- [ ] All 5 test files pass
- [ ] All 10 screens visible in both themes via simulator
- [ ] DesignPlaygroundView renders all 6 key screens in both themes
- [ ] FirstRunSheet appears on first launch only
- [ ] Theme persists across launches
- [ ] 20+ screenshots committed under `ios/docs/mockup-screenshots/`
- [ ] Signing dry-run succeeded; App Store Connect has build placeholder
- [ ] User has reviewed screenshots and explicitly approved direction → CHECKPOINT A
- [ ] Slice committed with `feat(ios): scaffold + mockup with both themes`

## 9. Estimated session count

**4–6 sessions** (roughly):
- Session 1: Tasks 0.1–0.4 (scaffold, themes, models)
- Session 2: Tasks 0.5–0.7 (mock data, Today, Detail)
- Session 3: Tasks 0.8–0.10 (Create/Edit, Analytics, Settings)
- Session 4: Tasks 0.11–0.12 (Auth/Onboarding, screenshots)
- Session 5: Task 0.13 + polish + user review fixes
- Session 6 (buffer): screenshot/visual fixes after user review

## 10. What unblocks the next slice

- User has signed off on visual direction (CHECKPOINT A)
- iOS app shell exists with mock auth + mock data — slice 02 will replace `MockData` calls in services with real `APIClient` calls
- Signing dry-run done — slice 11 can proceed with confidence later
- `ios/docs/mockup-screenshots/` becomes the visual regression baseline for all subsequent UI work

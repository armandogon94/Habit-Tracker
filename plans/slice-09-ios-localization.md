# Slice 09 — iOS Spanish + English localization (String Catalog)

> **Implements:** SPEC §1 "Spanish by default with English toggle in Settings", §8 "Settings → language toggle flips Spanish ↔ English live"
> **Status:** READY (depends on Slice 03 minimum; recommended after Slice 08 to localize all final strings at once)
> **Estimated sessions:** 2
> **Unblocks:** None directly

---

## 1. Objective

Add full Spanish localization with optional English toggle in Settings. Use Apple's modern String Catalog (`.xcstrings`). Default app language follows the user's chosen preference, persisted in App Group UserDefaults so the widget and Live Activity also localize correctly. **Spanish is the default** for new installs (matching the LATAM target audience). The toggle in Settings flips the entire app instantly via `Bundle` swap. Dates and numbers use `Locale` derived from the chosen language. All hardcoded strings audited and replaced with `String(localized:)`.

## 2. Pre-conditions

- [ ] Slice 03 done (most string surface exists)
- [ ] Slice 08 done is recommended (widget, notifications, Live Activity strings included)
- [ ] User confirms LATAM Spanish (es-419) acceptable vs es-ES; **default = `es`** (catch-all), can refine later

## 3. Files to create / modify

### Create
- `ios/HabitTracker/Localization/Localizable.xcstrings` — String Catalog with all keys, both languages
- `ios/HabitTracker/Core/Services/LanguageStore.swift` — `@Observable @MainActor`; `current: AppLanguage (.es | .en | .system)`; persists in App Group UserDefaults; provides `bundle: Bundle` (swapped via `Bundle.main.path(forResource: lang, ofType: "lproj")`)
- `ios/HabitTracker/Core/Services/LocalizedString.swift` — wrapper helpers: `L("key")`, `L("key", comment: "...")`, `L(plural: "key", count: n)`
- `ios/HabitTracker/Features/Settings/LanguageToggleView.swift`

### Modify (audit pass)
- Every `Text(...)`, `Label(...)`, alert, button, accessibility label across **all** Features and Core/ that currently has a literal string — replace with `L("key")`
- `HabitTrackerWidget/Views/*` — same
- `Core/Notifications/NotificationScheduler.swift` — notification body localized
- `Core/LiveActivity/HabitTimerLiveActivityView.swift` — localized
- `Features/Settings/SettingsView.swift` — link to LanguageToggleView
- `HabitTrackerApp.swift` — inject LanguageStore env

### Tests
- `ios/HabitTrackerTests/LocalizationKeysTests.swift` — every key in catalog has both `es` and `en` translations; no orphan keys
- `ios/HabitTrackerTests/LanguageStoreTests.swift` — switching changes Bundle; persists; default = es
- `ios/HabitTrackerTests/PluralizationTests.swift` — `"X habit / X habits"` and `"X hábito / X hábitos"` pluralize

### Tooling
- `Makefile` (root) — `make i18n-extract` runs `xcstringstool sync` to extract new keys
- CI (deferred to slice 11) — fail build if keys missing translations

---

## 4. Tasks

### Task 9.1 — String Catalog scaffold + LanguageStore + tests

**Description:** Create the catalog with ~10 seed keys; build LanguageStore + Bundle swap.

**Acceptance:**
- [ ] `Localizable.xcstrings` exists with English source and Spanish translations for ~10 keys (Settings titles, common buttons)
- [ ] `LanguageStore.current` defaults to `.es` (override `system` only if user explicitly picks)
- [ ] Switching language updates `LanguageStore.bundle`; SwiftUI views that consume `L("…")` re-render
- [ ] LanguageStoreTests + LocalizationKeysTests GREEN

**Verify:** `⌘U`; live: switch in Settings → Settings labels flip; restart app → choice persists.

**Files:** `Localization/Localizable.xcstrings`, `Core/Services/LanguageStore.swift`, `Core/Services/LocalizedString.swift`, `HabitTrackerTests/LanguageStoreTests.swift`, `HabitTrackerTests/LocalizationKeysTests.swift`

**Skills:** `swiftui-patterns`, `source-driven-development` (String Catalog docs), `test-driven-development`, `swift-concurrency-6-2`

---

### Task 9.2 — LanguageToggleView + Settings wiring

**Description:** Settings UI for language switching.

**Acceptance:**
- [ ] Three options: Sistema / Español / English (auto-localized)
- [ ] Tap → instant flip + persist
- [ ] Renders cleanly in both themes

**Verify:** Live.

**Files:** `Features/Settings/LanguageToggleView.swift`, `Features/Settings/SettingsView.swift`

**Skills:** `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design`

---

### Task 9.3 — String audit pass: Features

**Description:** Replace every literal string in `Features/` with `L("key")`. New keys auto-extract via `xcstringstool sync`. Translate Spanish.

**Acceptance:**
- [ ] No literal user-facing string in `Features/` (verified by grep + manual review)
- [ ] All keys present in catalog with both `es` and `en` values
- [ ] Tests pass with no missing-translation warnings

**Verify:**
```bash
cd ios && grep -rE 'Text\("|Label\("' HabitTracker/Features/ | grep -v "L(" | wc -l   # should be 0 (or only constants like icons)
```

**Files:** All files under `ios/HabitTracker/Features/`

**Skills:** `swiftui-patterns`, `code-simplification`

---

### Task 9.4 — String audit pass: Core, Widget, Notifications, Live Activity

**Description:** Same audit on supporting code.

**Acceptance:**
- [ ] Notification body and title localized
- [ ] Widget views localized
- [ ] Live Activity strings localized
- [ ] Error messages from APIError localized

**Verify:** Switch to Spanish → trigger notification → body in Spanish; widget in Spanish; Live Activity Stop button in Spanish.

**Files:** `Core/Notifications/*`, `HabitTrackerWidget/`, `Core/LiveActivity/*`, `Core/Networking/APIError.swift`

**Skills:** `swiftui-patterns`, `code-simplification`

---

### Task 9.5 — Pluralization, dates, numbers

**Description:** Use String Catalog `%lld` plural variants for "1 habit / N habits". Use `Date.FormatStyle` with current locale for all date displays. Numbers via `IntegerFormatStyle`.

**Acceptance:**
- [ ] All counts use plural keys (`"completed_count"` → "1 hábito completado" / "3 hábitos completados")
- [ ] All dates display via `.formatted(date: .abbreviated, time: .omitted)` and respect language locale
- [ ] PluralizationTests GREEN

**Verify:** Force counts of 0, 1, 2 in unit tests; visually check spelling in es vs en.

**Files:** `HabitTrackerTests/PluralizationTests.swift`, all view files using counts/dates

**Skills:** `swiftui-patterns`, `source-driven-development`, `test-driven-development`

---

### Task 9.6 — i18n extract Makefile target + docs

**Description:** Make extraction reproducible.

**Acceptance:**
- [ ] `make i18n-extract` runs catalog sync
- [ ] `docs/I18N.md` documents process for adding new keys + translation workflow
- [ ] Catalog committed with stub Spanish for any new keys (with `[Needs translation]` marker if not yet translated)

**Verify:** Add a new `L("test_key")` somewhere → run `make i18n-extract` → key appears in catalog.

**Files:** `Makefile` (root), `docs/I18N.md`

**Skills:** `documentation-and-adrs`, `ci-cd-and-automation`

---

## 5. Test plan

| File | Cases | Phase |
|---|---|---|
| `LocalizationKeysTests.swift` | `testEveryKeyHasESAndEN`, `testNoOrphanedKeysInCatalog` (parses .xcstrings JSON) | 9.1 |
| `LanguageStoreTests.swift` | `testDefaultIsSpanish`, `testSwitchPersists`, `testBundleReturnsExpected`, `testSystemFallsBackToOSPreference` | 9.1 |
| `PluralizationTests.swift` | `testCountZeroES`, `testCountOneES`, `testCountManyES`, same for EN | 9.5 |

---

## 6. Skills mapping

| Task | Primary | Secondary |
|---|---|---|
| 9.1 | `swiftui-patterns`, `source-driven-development`, `test-driven-development`, `swift-concurrency-6-2` | — |
| 9.2 | `swiftui-patterns`, `ios-hig-design`, `liquid-glass-design` | — |
| 9.3 | `swiftui-patterns`, `code-simplification` | — |
| 9.4 | `swiftui-patterns`, `code-simplification` | — |
| 9.5 | `swiftui-patterns`, `source-driven-development`, `test-driven-development` | — |
| 9.6 | `documentation-and-adrs`, `ci-cd-and-automation` | — |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Bundle swap doesn't propagate to all SwiftUI views without restart | Med | Use `@Environment(\.locale)` modifier on root + LanguageStore as `@Observable`; views read from store, not Bundle directly |
| Translations diverge as features change | Med | `xcstringstool sync` in CI; `[Needs translation]` markers; PR check |
| Pluralization rules differ by locale | Low | String Catalog handles plural variants natively |
| LATAM Spanish vs Spain Spanish word choices | Low | Use neutral Spanish (es); document choices in I18N.md |
| Date formatting in widget extension may use wrong locale | Med | Widget reads LanguageStore via App Group; same Bundle path |
| Existing screenshots from slice 00 are English-only | Low | Re-take key screenshots in Spanish for slice-11 marketing |

---

## 8. Definition of done

- [ ] All test files in §5 GREEN
- [ ] App launches in Spanish on fresh install
- [ ] Settings → Language → English → entire app flips immediately
- [ ] Notifications, widget, Live Activity all localize
- [ ] No literal user-facing strings remain (grep clean)
- [ ] `docs/I18N.md` documents the workflow
- [ ] Spanish screenshots committed under `ios/docs/mockup-screenshots/es/`
- [ ] Slice committed: `feat(ios): full Spanish + English localization with in-app toggle`

## 9. Estimated session count

**2 sessions:**
- Session 1: Tasks 9.1 + 9.2 + 9.5 (foundation + Settings UI + plurals)
- Session 2: Tasks 9.3 + 9.4 + 9.6 (audit passes + Makefile + docs)

## 10. What unblocks the next slice

- iOS app is feature-complete and localized — ready for stakeholder dogfood (CHECKPOINT D)
- Slice 10 (web admin) can proceed; nothing in admin depends on iOS
- Slice 11 (TestFlight) has the final binary surface to ship

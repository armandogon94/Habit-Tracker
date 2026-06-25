# Slice 02 — iOS auth wired to backend (Keychain, APIClient, AuthService)

> **Implements:** SPEC §2 iOS networking + security stack, §8 iOS auth criteria
> **Status:** READY (depends on Slice 00 + Slice 01)
> **Estimated sessions:** 3
> **Unblocks:** Slice 03 (real bearer tokens needed for habits API)

---

## 1. Objective

Replace the mock auth flow from Slice 00 with real backend auth. Build the iOS networking layer end-to-end: `APIConfig` (env-aware base URL), `APIClient` (URLSession + async/await + auto-refresh + retry-once), `APIError`, `KeychainTokenStore` (Keychain Services for refresh; in-memory access token), `AuthService` (login/register/logout/me). Wire into existing LoginView and RegisterView. After this slice, sign-in talks to the real `/auth/login-mobile`, refresh tokens persist across app restarts via Keychain, and 401 responses trigger a single transparent refresh + retry.

## 2. Pre-conditions

- [ ] Slice 00 done: iOS app skeleton + LoginView/RegisterView (mock)
- [ ] Slice 01 done: `/auth/login-mobile`, `/auth/refresh-mobile` reachable
- [ ] Backend running on `http://localhost:8020` (simulator can hit it)
- [ ] One known-good user: `demo@test.com` / `password123`

## 3. Files to create / modify

### Create
- `ios/HabitTracker/Core/Networking/APIConfig.swift` — `enum Environment { case dev, staging, prod }` with `baseURL` per case; current env compiled in via Xcode build setting (Debug = dev)
- `ios/HabitTracker/Core/Networking/APIError.swift` — typed error enum (`unauthorized`, `notFound`, `validation([String])`, `server(Int, String)`, `network`, `decoding`, `unknown`)
- `ios/HabitTracker/Core/Networking/DTO.swift` — request/response DTOs matching backend exactly (`LoginRequest`, `RegisterRequest`, `MobileTokenResponse`, `RefreshRequest`, `UserResponse`)
- `ios/HabitTracker/Core/Networking/APIClient.swift` — actor; `request<T: Decodable>(_:body:auth:)`; auto-refresh on 401; uses `JSONDecoder` with snake_case strategy
- `ios/HabitTracker/Core/Security/KeychainTokenStore.swift` — actor; `saveRefresh(_)`, `loadRefresh()`, `deleteRefresh()`; access token in-memory only
- `ios/HabitTracker/Core/Services/AuthService.swift` — `login`, `register`, `refresh`, `logout`, `me`; updates Keychain + APIClient state
- `ios/HabitTracker/Core/Services/AuthState.swift` — `@Observable @MainActor` source of truth for "am I signed in?", current `User`

### Modify
- `ios/HabitTracker/HabitTrackerApp.swift` — inject `APIClient`, `KeychainTokenStore`, `AuthService`, `AuthState` as env values
- `ios/HabitTracker/RootView.swift` — switch on `AuthState.status` (`.signedOut → LoginView`, `.signedIn → TabView`)
- `ios/HabitTracker/Features/Auth/LoginView.swift` — call `AuthService.login`; show inline error from `APIError`; loading state
- `ios/HabitTracker/Features/Auth/RegisterView.swift` — call `AuthService.register`; same UX
- `ios/HabitTracker/Features/Settings/SettingsView.swift` — Sign Out button calls `AuthService.logout`
- `ios/HabitTracker/Features/Onboarding/FirstRunSheet.swift` — still shows on first launch, but only AFTER successful sign-in (or once, on app first launch)

### Tests
- `ios/HabitTrackerTests/APIClientTests.swift` — mock URLSession; 200/401-then-200 (refresh)/401-then-401, decoding, error mapping
- `ios/HabitTrackerTests/KeychainTokenStoreTests.swift` — save/load/delete; uses test keychain access group
- `ios/HabitTrackerTests/AuthServiceTests.swift` — login happy path, login wrong password, register duplicate, logout clears Keychain
- `ios/HabitTrackerTests/DTOTests.swift` — encode/decode for all DTOs against fixture JSON

### Add fixture
- `ios/HabitTrackerTests/Fixtures/login-success.json`, `login-401.json`, `me-success.json` — captured from real backend curl

---

## 4. Tasks

### Task 2.1 — APIConfig + APIError + DTO + tests

**Description:** Foundation types. Environment-aware base URL (dev = `http://localhost:8020`, prod = `https://api.habits.armandointeligencia.com`). DTOs match backend `MobileTokenResponse` shape exactly.

**Acceptance:**
- [ ] `APIConfig.current` resolves to `.dev` in Debug, `.prod` in Release
- [ ] DTOs decode fixture JSON byte-perfect
- [ ] `APIError` cases cover 401, 404, 422 (validation), 5xx, network, decoding
- [ ] All `DTOTests` GREEN

**Verify:** `⌘U` on `DTOTests` GREEN.

**Files:** `Core/Networking/APIConfig.swift`, `Core/Networking/APIError.swift`, `Core/Networking/DTO.swift`, `HabitTrackerTests/DTOTests.swift`, `HabitTrackerTests/Fixtures/*.json`

**Skills:** `swift-protocol-di-testing`, `swift-concurrency-6-2`, `test-driven-development`, `source-driven-development` (Codable docs, JSONDecoder strategies)

---

### Task 2.2 — KeychainTokenStore + tests

**Description:** Actor-isolated Keychain wrapper for the refresh token. Access token stays in process memory only.

**Acceptance:**
- [ ] `actor KeychainTokenStore`; methods `saveRefresh`, `loadRefresh`, `deleteRefresh`
- [ ] Service identifier: `com.armandointeligencia.HabitTracker.refresh`
- [ ] Access controls: `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`
- [ ] Tests use a unique service id per test to avoid pollution
- [ ] All `KeychainTokenStoreTests` GREEN

**Verify:** `⌘U` GREEN; manually delete app → token gone.

**Files:** `Core/Security/KeychainTokenStore.swift`, `HabitTrackerTests/KeychainTokenStoreTests.swift`

**Skills:** `swift-actor-persistence`, `security-and-hardening`, `test-driven-development`, `source-driven-development` (Keychain Services docs)

---

### Task 2.3 — APIClient with auto-refresh + tests

**Description:** Single actor. `request<T>(_ endpoint, body:, requiresAuth:)`. On 401 with `requiresAuth`, attempts ONE refresh; on success, retries the original request once. On second 401 or refresh failure, signs the user out (publishes via `AuthState`).

**Acceptance:**
- [ ] `APIClient` is an `actor`
- [ ] `setAccessToken(_)` and `clearTokens()` methods
- [ ] Refresh path uses `KeychainTokenStore.loadRefresh()` then calls `/auth/refresh-mobile`
- [ ] Single in-flight refresh: concurrent 401s share one refresh task (uses `Task` + checked continuation)
- [ ] Tests with mocked `URLProtocol` cover: 200 OK, 401-refresh-success-retry-200, 401-refresh-401-signout, 500-no-retry, network error
- [ ] All `APIClientTests` GREEN

**Verify:** `⌘U` GREEN.

**Files:** `Core/Networking/APIClient.swift`, `HabitTrackerTests/APIClientTests.swift`, `HabitTrackerTests/Helpers/MockURLProtocol.swift`

**Skills:** `swift-concurrency-6-2`, `swift-protocol-di-testing`, `test-driven-development`, `source-driven-development` (URLSession async)

---

### Task 2.4 — AuthService + AuthState + tests

**Description:** High-level auth surface. `AuthState` is the `@Observable @MainActor` truth; `AuthService` mutates it.

**Acceptance:**
- [ ] `AuthState.status: .signedOut | .signedIn(User) | .checking`
- [ ] `AuthService.login(email:, password:)` → on success, saves refresh, sets access in APIClient, sets `AuthState.status = .signedIn(user)`
- [ ] `AuthService.register(email:, password:, timezone:)` → same
- [ ] `AuthService.logout()` → calls `/auth/logout-mobile`, clears Keychain + access, sets `.signedOut`
- [ ] `AuthService.restoreSession()` (called on app launch) → if Keychain has refresh, attempts refresh + `/auth/me`; on success → signed in
- [ ] All `AuthServiceTests` GREEN with mocked APIClient

**Verify:** `⌘U` GREEN.

**Files:** `Core/Services/AuthService.swift`, `Core/Services/AuthState.swift`, `HabitTrackerTests/AuthServiceTests.swift`

**Skills:** `swift-actor-persistence`, `swift-concurrency-6-2`, `swift-protocol-di-testing`, `test-driven-development`

---

### Task 2.5 — Wire LoginView, RegisterView, RootView

**Description:** Replace mock auth in views with real `AuthService` calls. RootView gates on `AuthState`.

**Acceptance:**
- [ ] LoginView: typing + tap → `AuthService.login` → on success, RootView flips to TabView
- [ ] LoginView: 401 shows red inline message "Invalid credentials"; 429 shows "Too many attempts"; network shows "No connection"
- [ ] RegisterView: same UX patterns; 409 shows "Email already in use"
- [ ] App launch: `AuthService.restoreSession()` runs; if refresh token in Keychain works → straight to Today; else → LoginView
- [ ] Sign Out from Settings clears state; back to LoginView
- [ ] FirstRunSheet appears only on app's first launch (UserDefaults flag), independent of auth

**Verify:** Manual flow in simulator: sign in → close app → reopen → still signed in. Sign out → reopen → LoginView.

**Files:** `RootView.swift`, `Features/Auth/LoginView.swift`, `Features/Auth/RegisterView.swift`, `Features/Settings/SettingsView.swift`, `HabitTrackerApp.swift`

**Skills:** `swiftui-patterns`, `ios-hig-design`, `frontend-ui-engineering`, `swift-concurrency-6-2`

---

## 5. Test plan (RED → GREEN order)

| Test file | Cases | Phase |
|---|---|---|
| `DTOTests.swift` | `testLoginRequestEncoding`, `testMobileTokenResponseDecoding`, `testUserResponseDecoding`, `testValidationErrorDecoding` | 2.1 |
| `KeychainTokenStoreTests.swift` | `testSaveAndLoad`, `testDelete`, `testOverwriteExisting`, `testMissingReturnsNil` | 2.2 |
| `APIClientTests.swift` | `test200OK`, `test401TriggersRefreshAndRetry`, `testRefreshFailureSignsOut`, `test500NoRetry`, `testConcurrent401sShareOneRefresh`, `testNetworkErrorMaps` | 2.3 |
| `AuthServiceTests.swift` | `testLoginSuccessSetsState`, `testLoginInvalidCredentialsMaps401`, `testRegisterSuccess`, `testRegisterDuplicate409`, `testLogoutClearsKeychain`, `testRestoreSessionWithValidRefresh`, `testRestoreSessionWithInvalidRefresh` | 2.4 |

All RED first; verify they fail with intentional error, then implement.

---

## 6. Skills mapping (per task)

| Task | Primary | Secondary |
|---|---|---|
| 2.1 | `swift-protocol-di-testing`, `swift-concurrency-6-2`, `test-driven-development` | `source-driven-development` |
| 2.2 | `swift-actor-persistence`, `security-and-hardening`, `test-driven-development` | `source-driven-development` |
| 2.3 | `swift-concurrency-6-2`, `test-driven-development`, `swift-protocol-di-testing` | `source-driven-development` |
| 2.4 | `swift-actor-persistence`, `swift-concurrency-6-2`, `test-driven-development` | — |
| 2.5 | `swiftui-patterns`, `ios-hig-design`, `frontend-ui-engineering` | `swift-concurrency-6-2` |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Concurrent 401s trigger N refreshes (server hammered + race) | Med | Single in-flight refresh task; tested explicitly |
| Keychain ACL too strict → re-prompt user | Low | `AccessibleAfterFirstUnlockThisDeviceOnly` — works after first device unlock per boot |
| iOS App Transport Security blocks `http://localhost` | High | `NSAppTransportSecurity.NSAllowsLocalNetworking = true` in Info.plist (already set in 04 reference) |
| Refresh token leaked via logs | High | `KeychainTokenStore` never logs tokens; APIClient redacts `Authorization` header in logs |
| User signs in on web → has cookie session, but iOS uses different refresh — confusion | Low | Document in user-facing release notes; auth stores are independent by design |

---

## 8. Definition of done

- [ ] All test files in §5 GREEN
- [ ] Real sign-in works against `localhost:8020` with `demo@test.com`/`password123`
- [ ] Cold restart preserves session via Keychain
- [ ] Sign Out clears Keychain (verify via Keychain dump or by reinstall)
- [ ] 401 on a habits call (forced via expired access token) triggers refresh + retry once, transparent to user
- [ ] No tokens visible in Console.app logs
- [ ] Slice committed: `feat(ios): real auth, keychain, apiclient with refresh`

## 9. Estimated session count

**3 sessions:**
- Session 1: Tasks 2.1 + 2.2 (DTOs + Keychain)
- Session 2: Task 2.3 (APIClient with refresh — biggest)
- Session 3: Task 2.4 + 2.5 (AuthService + view wiring)

## 10. What unblocks the next slice

- iOS has working bearer-token auth — slice 03 can build `HabitsService` on top of `APIClient` immediately
- `restoreSession` flow proves the refresh round-trip works end-to-end
- Mock auth code is gone from views, app code is now the auth source of truth

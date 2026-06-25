# Slice 11 — TestFlight prep + signing + first build + production hardening

> **Implements:** SPEC §8 "Personal TestFlight build installable", §11 deferred tech debt items 4, 9, 10, 12
> **Status:** FINAL slice (depends on slices 00–10 done)
> **Estimated sessions:** 3
> **Unblocks:** Family/friends invites; production launch

---

## 1. Objective

Ship the app. Resolve all deferred tech debt items that were blocked on "iOS first": prod CORS, secure cookies, prod docker-compose, CI/CD. On the iOS side: app icon, marketing screenshots, App Store Connect metadata, TestFlight internal + external testing groups, signing certificates, App Store review information. On the backend side: deploy production stack with Traefik, HTTPS, real DB password, Redis, monitoring. Sanity-check everything with a fresh-device install via TestFlight as Armando, then expand the tester group to family.

## 2. Pre-conditions

- [ ] All slices 00–10 complete and merged to main
- [ ] Slice 00 Task 0.13 (signing dry-run) succeeded — we know signing works
- [ ] Apple Developer account active; App Store Connect access confirmed
- [ ] VPS (existing one for habits.armandointeligencia.com) accessible
- [ ] Domain DNS for `habits.armandointeligencia.com` and `api.habits.armandointeligencia.com` resolves to VPS

## 3. Files to create / modify

### Backend / Infra
- `docker-compose.prod.yml` — Traefik, postgres (or shared), redis, backend, frontend; HTTPS via Let's Encrypt; real env vars
- `traefik/traefik.yml` (or labels-only via compose) — config
- `backend/Dockerfile` — confirm production-ready (multi-stage, non-root user, healthcheck)
- `frontend/Dockerfile` — confirm `output: "standalone"`, multi-stage
- `backend/app/main.py` — CORS hardened: env-driven origin list (`https://habits.armandointeligencia.com` for prod)
- `backend/app/routers/auth.py` — cookie `secure=True` when `ENVIRONMENT=prod`
- `.github/workflows/ci.yml` — lint + test on push (backend pytest, frontend vitest, iOS XCTest)
- `.github/workflows/deploy.yml` — on tag push, build + push images, ssh to VPS, `docker compose -f docker-compose.prod.yml up -d`
- `Makefile` — `make deploy` target

### iOS
- `ios/HabitTracker/Resources/Assets.xcassets/AppIcon.appiconset/` — full icon set (1024 + all sizes)
- `ios/docs/AppStoreConnect/` — folder with App Store Connect metadata draft (description, keywords, privacy policy URL, support URL)
- `ios/docs/TestFlight-onboarding.md` — instructions for testers
- `ios/HabitTracker/Resources/PrivacyInfo.xcprivacy` — Apple privacy manifest (required for App Store submission)
- `ios/project.yml` — Release config: archive scheme; `MARKETING_VERSION`, `CURRENT_PROJECT_VERSION` set; bitcode disabled (Apple removed it but be explicit); ATS hardened (drop `NSAllowsLocalNetworking` in Release)

### Docs
- `docs/DEPLOYMENT.md` — full prod deploy runbook
- `docs/INCIDENT-RESPONSE.md` — what to do if prod goes down
- `docs/PRIVACY.md` — privacy policy text (required by App Store)

---

## 4. Tasks

### Task 11.1 — Production backend hardening + tests

**Description:** Tighten CORS, cookies, secrets. Verify with tests.

**Acceptance:**
- [ ] `Settings.environment: Literal["dev","staging","prod"]`
- [ ] CORS origins list driven by env: prod = `["https://habits.armandointeligencia.com"]`
- [ ] Cookie `secure=True` and `samesite="strict"` when `environment=="prod"`
- [ ] `JWT_SECRET` rotated to a new strong value for prod
- [ ] `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` in `.env.prod` (gitignored)
- [ ] Tests: `test_cors_prod_blocks_other_origin`, `test_cookie_secure_in_prod`
- [ ] All web flows still pass

**Verify:** `ENVIRONMENT=prod uv run pytest tests/`.

**Files:** `app/core/config.py`, `app/main.py` (CORS), `app/routers/auth.py` (cookie), `tests/test_cors_prod.py`, `tests/test_cookie_prod.py`

**Skills:** `security-and-hardening`, `test-driven-development`, `documentation-and-adrs`

---

### Task 11.2 — docker-compose.prod.yml + Traefik + HTTPS

**Description:** Full prod stack.

**Acceptance:**
- [ ] `docker-compose.prod.yml` defines: `traefik`, `backend`, `frontend`, `redis`, (optional) `postgres` (or external)
- [ ] Traefik routes: `habits.armandointeligencia.com` → frontend; `api.habits.armandointeligencia.com` → backend
- [ ] HTTPS via Let's Encrypt (certificatesResolvers)
- [ ] Healthchecks on backend (`/health`)
- [ ] Restart policy `unless-stopped`
- [ ] `docker compose -f docker-compose.prod.yml config` validates
- [ ] `make deploy` target ssh's to VPS and runs the compose

**Verify:**
```bash
docker compose -f docker-compose.prod.yml config
# On VPS:
docker compose -f docker-compose.prod.yml up -d
curl https://api.habits.armandointeligencia.com/health  # 200
curl https://habits.armandointeligencia.com  # 200
```

**Files:** `docker-compose.prod.yml`, `traefik/` (configs if any), `Makefile`, `docs/DEPLOYMENT.md`

**Skills:** `ci-cd-and-automation`, `documentation-and-adrs`, `security-and-hardening`, `source-driven-development` (Traefik docs)

---

### Task 11.3 — GitHub Actions CI/CD

**Description:** Lint + test on every push; deploy on tag.

**Acceptance:**
- [ ] `.github/workflows/ci.yml`:
  - Backend: `uv sync && uv run ruff check && uv run pytest`
  - Frontend: `npm ci && npm run lint && npm test`
  - iOS: macOS runner; `xcodegen && xcodebuild test -scheme HabitTracker -destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=26.0'`
- [ ] `.github/workflows/deploy.yml`:
  - Trigger on `push tag v*`
  - Build backend + frontend images, push to GHCR
  - SSH to VPS, run `make deploy`
- [ ] Branch protection: PRs need CI green before merge

**Verify:** Push a small commit → CI runs all 3 suites; tag a test version → deploy fires.

**Files:** `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`

**Skills:** `ci-cd-and-automation`, `source-driven-development` (GitHub Actions docs)

---

### Task 11.4 — App icon + privacy manifest + App Store Connect setup

**Description:** Apple-required artifacts.

**Acceptance:**
- [ ] App icon set complete (1024 marketing + all device sizes)
- [ ] `PrivacyInfo.xcprivacy` manifest declares: data not linked to user (we collect email + analytics? document everything we touch)
- [ ] App Store Connect record exists: title, bundle id, primary lang Spanish
- [ ] Description, keywords, support URL, privacy policy URL set
- [ ] Marketing screenshots: 5 per device size (iPhone 16 Pro Max, iPhone 16 Pro) in Spanish
- [ ] Build metadata: version 1.0.0, build 1

**Verify:** App Store Connect "Ready to Submit for Review" preflight passes (or only blocks on the build itself).

**Files:** `ios/HabitTracker/Resources/Assets.xcassets/AppIcon.appiconset/*`, `ios/HabitTracker/Resources/PrivacyInfo.xcprivacy`, `ios/docs/AppStoreConnect/description.es.md`, `keywords.es.txt`, `screenshots/` (drag into ASC by hand)

**Skills:** `shipping-and-launch`, `documentation-and-adrs`, `ios-hig-design`

---

### Task 11.5 — TestFlight build + internal test

**Description:** Archive + upload + invite Armando as internal tester.

**Acceptance:**
- [ ] `xcodebuild archive` succeeds (Release config)
- [ ] Build uploaded via `xcodebuild -exportArchive` or Xcode Organizer
- [ ] Build appears in App Store Connect → TestFlight tab
- [ ] Internal testing group has Armando; install on device via TestFlight app
- [ ] Smoke test on real device: sign in, log a habit, see widget, fire a notification, start Live Activity, switch theme, switch language

**Verify:** TestFlight build installs on physical iPhone running iOS 26.

**Files:** none — process artifacts captured in `ios/docs/SIGNING.md`

**Skills:** `shipping-and-launch`

---

### Task 11.6 — TestFlight external test + family invites

**Description:** Add an external testing group, invite family members.

**Acceptance:**
- [ ] External group "Family" created in App Store Connect
- [ ] Build distributed to external group (requires Apple beta review — auto-approved typically in 24h for non-major changes)
- [ ] Family members receive TestFlight invite email
- [ ] At least 1 family member installs and successfully logs a habit

**Verify:** Confirm with one tester via direct message.

**Files:** `ios/docs/TestFlight-onboarding.md` (Spanish instructions for non-technical family)

**Skills:** `shipping-and-launch`, `documentation-and-adrs`

---

### Task 11.7 — Monitoring + incident response docs

**Description:** Basic observability so we know if prod breaks.

**Acceptance:**
- [ ] Backend writes structured logs (JSON) to stdout; visible via `docker logs`
- [ ] Add `/health` endpoint returning DB + Redis status
- [ ] Set up uptime monitoring (UptimeRobot or similar) on `https://api.habits.armandointeligencia.com/health`
- [ ] `docs/INCIDENT-RESPONSE.md`: what to check, how to roll back via `docker compose down && git checkout <prev-tag> && docker compose up -d`

**Verify:** Trigger fake outage (stop backend container) → uptime monitor alerts within 5 min.

**Files:** `app/main.py` (`/health`), `docs/INCIDENT-RESPONSE.md`

**Skills:** `shipping-and-launch`, `documentation-and-adrs`, `ci-cd-and-automation`

---

## 5. Test plan

| File | Cases | Phase |
|---|---|---|
| `test_cors_prod.py` | `test_prod_blocks_unknown_origin`, `test_prod_allows_known_origin` | 11.1 |
| `test_cookie_prod.py` | `test_cookie_secure_in_prod`, `test_cookie_samesite_strict_in_prod`, `test_cookie_secure_false_in_dev` | 11.1 |
| Existing test suites | All must remain GREEN under `ENVIRONMENT=prod` | 11.1 |
| CI workflow | Sanity: `gh workflow run ci.yml` returns success on a clean PR | 11.3 |

---

## 6. Skills mapping

| Task | Primary | Secondary |
|---|---|---|
| 11.1 | `security-and-hardening`, `test-driven-development`, `documentation-and-adrs` | — |
| 11.2 | `ci-cd-and-automation`, `documentation-and-adrs`, `security-and-hardening`, `source-driven-development` | — |
| 11.3 | `ci-cd-and-automation`, `source-driven-development` | `documentation-and-adrs` |
| 11.4 | `shipping-and-launch`, `documentation-and-adrs`, `ios-hig-design` | — |
| 11.5 | `shipping-and-launch` | — |
| 11.6 | `shipping-and-launch`, `documentation-and-adrs` | — |
| 11.7 | `shipping-and-launch`, `documentation-and-adrs`, `ci-cd-and-automation` | — |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Apple rejects build for missing privacy info | Med | `PrivacyInfo.xcprivacy` complete and accurate; review Apple docs current at submission time |
| Let's Encrypt rate limit on first deploy | Low | Use staging cert resolver first; switch to prod once verified |
| Push to prod takes site down | High | Maintenance window scheduled; rollback is `git checkout previous-tag && make deploy` |
| Family member confused by TestFlight install | Low | `TestFlight-onboarding.md` with screenshots in Spanish |
| Database migration on prod fails halfway | High | Backup DB pre-migration; tested migrations on staging copy first |
| Apple beta review takes longer than 24h | Low | Schedule release with buffer; send internal first |
| Secrets accidentally checked into commit | High | Pre-commit hook from slice 01; `.env.prod` in `.gitignore`; verified clean before tag |
| Traefik HTTPS misconfig → users see cert warning | High | Verify cert via `openssl s_client` before announcing |

---

## 8. Definition of done

- [ ] All deferred tech debt items 4, 9, 10, 12 closed
- [ ] CI runs on every push; deploy runs on tag
- [ ] Production stack live: `https://habits.armandointeligencia.com` and `https://api.habits.armandointeligencia.com` reachable with valid certs
- [ ] iOS app installable from TestFlight on Armando's iPhone
- [ ] At least 1 family member installed and logged a habit successfully
- [ ] Uptime monitor active and alerting
- [ ] Documentation complete: DEPLOYMENT.md, INCIDENT-RESPONSE.md, PRIVACY.md, TestFlight-onboarding.md
- [ ] Slice committed: `chore(release): v1.0.0 — TestFlight + production hardening`
- [ ] Tag `v1.0.0` pushed
- [ ] CHECKPOINT F reached: TestFlight invites sent, production live

## 9. Estimated session count

**3 sessions:**
- Session 1: Tasks 11.1 + 11.2 (backend hardening + prod compose)
- Session 2: Task 11.3 + 11.4 (CI/CD + App Store Connect setup)
- Session 3: Tasks 11.5 + 11.6 + 11.7 (TestFlight + family + monitoring)

## 10. What unblocks the next thing

- Project ships
- App Store submission (separate v1.1 work) → no longer in scope of this plan; create new spec when ready
- Telemetry from real users informs v2 backlog (HealthKit, Watch, Siri Shortcuts, social features)
- Ongoing maintenance follows the established CI/CD + admin tools loop

---

## Post-ship retrospective checklist

- [ ] Capture what went well + what was painful in `docs/RETRO-v1.0.md`
- [ ] Update `.claude/memory.md` with hard-won lessons for future Claude Code sessions
- [ ] Run `/review` skill on the full release diff
- [ ] Inventory any deferred items into a `BACKLOG.md` for v1.1

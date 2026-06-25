# Slice 10 — Web admin route group + admin endpoints + UI

> **Implements:** SPEC §1 "Web admin", §8 web criteria, §9 Q4 (4 KPI cards + 1 line chart)
> **Status:** READY (depends on Slice 01 only — `users.role` + role claim in JWT). Fully parallelizable with iOS slices 04–09.
> **Estimated sessions:** 3–4
> **Unblocks:** Slice 11 partially (web also gets shipped together)

---

## 1. Objective

Add an `(admin)` route group to the existing Next.js app, gated by JWT role claim. Provide three admin pages: **Users** (list, suspend, delete), **Metrics** (4 KPI cards + 1 line chart), **Logs** (manual habit-log editor for support / data fix). Backend exposes `/api/v1/admin/*` endpoints, all guarded by `require_admin` (built in slice 01). Audit log every admin action. Reuse existing TanStack Query patterns; create a small admin component library that we can also reuse for slice 11 monitoring dashboards if needed.

## 2. Pre-conditions

- [ ] Slice 01 done — `users.role` enum + `require_admin` dependency
- [ ] Demo admin user exists: `UPDATE users SET role='admin' WHERE email='demo@test.com';`
- [ ] Web frontend currently runs at `localhost:3020`
- [ ] JWT in localStorage (web)? — slice 01 web flow uses cookie; we use `/auth/me` to derive role for client-side gating; server-side gating is the source of truth

## 3. Files to create / modify

### Backend create
- `backend/app/routers/admin.py` — `/users`, `/users/{id}/suspend`, `/users/{id}` (DELETE), `/metrics`, `/metrics/logs-per-day`, `/logs/{id}` (PATCH), `/audit` (GET)
- `backend/app/services/admin_service.py` — business logic + audit
- `backend/app/models/audit_log.py` — `AuditLog` model: actor_id, action, target_type, target_id, payload (jsonb), created_at
- `backend/alembic/versions/<auto>_create_audit_log.py`
- `backend/app/schemas/admin.py` — `AdminUserResponse`, `MetricsResponse`, `LogsPerDayResponse`, `UpdateLogRequest`, `AuditLogResponse`
- `backend/tests/routers/test_admin.py` — full coverage: authz, CRUD, metrics math, audit emission
- `backend/tests/services/test_admin_service.py`

### Backend modify
- `backend/app/main.py` — mount admin router

### Web create
- `frontend/src/app/(admin)/layout.tsx` — server-side guard: redirect non-admin to `/habits`; admin nav (Users / Metrics / Logs)
- `frontend/src/app/(admin)/users/page.tsx`
- `frontend/src/app/(admin)/metrics/page.tsx`
- `frontend/src/app/(admin)/logs/page.tsx`
- `frontend/src/components/admin/UsersTable.tsx`
- `frontend/src/components/admin/MetricsKPICard.tsx`
- `frontend/src/components/admin/LogsPerDayChart.tsx` — Recharts LineChart
- `frontend/src/components/admin/LogEditor.tsx` — search log by id or user, edit `completed_date`/`note`, delete
- `frontend/src/components/admin/AuditLogList.tsx`
- `frontend/src/components/admin/Toast.tsx` — generic toast for actions (also fixes tech debt #11 partially)
- `frontend/src/components/admin/ConfirmDialog.tsx`
- `frontend/src/hooks/useAdminUsers.ts`
- `frontend/src/hooks/useAdminMetrics.ts`
- `frontend/src/hooks/useAdminLogs.ts`
- `frontend/src/lib/api.ts` — extend with admin endpoint helpers

### Web modify
- `frontend/src/lib/auth.tsx` — expose `role` from `/auth/me`
- `frontend/src/components/layout/*` — admin badge if role=admin

### Tests
- `frontend/__tests__/admin/admin-guard.test.tsx` — non-admin redirect
- `frontend/__tests__/admin/users-table.test.tsx`
- `frontend/__tests__/admin/metrics.test.tsx`
- `frontend/__tests__/admin/log-editor.test.tsx`

---

## 4. Tasks

### Task 10.1 — Audit log model + migration

**Description:** Persist every admin action.

**Acceptance:**
- [ ] `audit_logs` table created
- [ ] Migration applied; reversible
- [ ] `AuditLog` model + factory
- [ ] Helper `record_audit(actor_id, action, target_type, target_id, payload)` available

**Verify:** `uv run alembic upgrade head` then `psql -c "\d audit_logs"`.

**Files:** `app/models/audit_log.py`, `alembic/versions/<auto>_create_audit_log.py`, `app/services/admin_service.py` (helper)

**Skills:** `database-migrations`, `security-and-hardening`

---

### Task 10.2 — Admin user endpoints + tests

**Description:** List, suspend, delete users.

**Acceptance:**
- [ ] `GET /api/v1/admin/users?page=&size=&search=` → paginated; admin-only
- [ ] `POST /api/v1/admin/users/{id}/suspend` → adds `is_suspended` flag (new column on users) + audit
- [ ] `DELETE /api/v1/admin/users/{id}` → soft-delete + audit (cascade habits soft-delete via slice 05 tombstones)
- [ ] All endpoints reject non-admin with 403
- [ ] Pagination tested
- [ ] Tests cover happy + 403 + 404

**Verify:** `uv run pytest tests/routers/test_admin.py::TestUsers -v`.

**Files:** `app/routers/admin.py`, `app/services/admin_service.py`, `app/schemas/admin.py`, `app/models/user.py` (add `is_suspended`, `deleted_at`), `alembic/versions/<auto>_user_suspended_deleted.py`, `tests/routers/test_admin.py`

**Skills:** `api-and-interface-design`, `security-and-hardening`, `test-driven-development`, `database-migrations`

---

### Task 10.3 — Metrics endpoints + tests

**Description:** Per resolved Q4: 4 KPIs + logs/day for 30 days.

**Acceptance:**
- [ ] `GET /api/v1/admin/metrics` returns:
  - `total_users` (excluding deleted)
  - `dau_24h` (distinct users with a habit_log inserted in last 24h)
  - `logs_today` (count of habit_logs with completed_date = today UTC)
  - `errors_24h` (count of error rows in audit_log of type 'error' OR an OS-level error counter — start with 0 stub if not wired; document)
- [ ] `GET /api/v1/admin/metrics/logs-per-day?days=30` returns `[{date, count}]`
- [ ] Both admin-only
- [ ] Math verified by tests with seeded fixtures

**Verify:** `uv run pytest tests/routers/test_admin.py::TestMetrics -v`.

**Files:** `app/routers/admin.py`, `app/services/admin_service.py` (metrics math), `tests/routers/test_admin.py`

**Skills:** `api-and-interface-design`, `database-migrations`, `performance-optimization` (these queries should be fast — index review), `test-driven-development`

---

### Task 10.4 — Log editor endpoints + tests

**Description:** Admin can fix a wrong habit log.

**Acceptance:**
- [ ] `GET /api/v1/admin/logs?user_email=&date=` returns logs matching filter
- [ ] `PATCH /api/v1/admin/logs/{id}` updates `completed_date` or `note`; audit
- [ ] `DELETE /api/v1/admin/logs/{id}` removes log; audit
- [ ] Admin-only
- [ ] Tests

**Verify:** `uv run pytest tests/routers/test_admin.py::TestLogs -v`.

**Files:** `app/routers/admin.py`, `app/services/admin_service.py`, `tests/routers/test_admin.py`

**Skills:** `api-and-interface-design`, `security-and-hardening`, `test-driven-development`

---

### Task 10.5 — Web (admin) layout + guard

**Description:** Route group with server-side role check. Non-admin → redirect.

**Acceptance:**
- [ ] `(admin)/layout.tsx` reads role from server-side fetch to `/auth/me` (uses cookie); if not admin → `redirect('/habits')`
- [ ] Layout includes admin nav (3 tabs)
- [ ] Tests verify non-admin gets redirected (admin-guard.test.tsx)

**Verify:** Manual: visit `/admin/users` as non-admin → redirected; as admin → page loads.

**Files:** `frontend/src/app/(admin)/layout.tsx`, `frontend/src/lib/auth.tsx`, `frontend/__tests__/admin/admin-guard.test.tsx`

**Skills:** `security-and-hardening`, `frontend-ui-engineering`, `swiftui-patterns` (n/a — web; substitute `frontend-patterns` if added)

---

### Task 10.6 — UsersTable page + components

**Description:** Searchable, paginated user list with row actions (Suspend, Delete) + ConfirmDialog + Toast.

**Acceptance:**
- [ ] Page renders users with email, created_at, role, is_suspended, last_active
- [ ] Search box debounced 300ms
- [ ] Suspend → confirms → calls API → toast on success
- [ ] Delete → confirms (typed-confirm) → calls API → toast
- [ ] All admin actions show in audit list
- [ ] Tests cover render, action, error path

**Verify:** Manual + `npm test users-table`.

**Files:** `frontend/src/app/(admin)/users/page.tsx`, `frontend/src/components/admin/UsersTable.tsx`, `Toast.tsx`, `ConfirmDialog.tsx`, `frontend/src/hooks/useAdminUsers.ts`, `frontend/__tests__/admin/users-table.test.tsx`

**Skills:** `frontend-ui-engineering`, `swiftui-patterns` (n/a; use general patterns), `test-driven-development`

---

### Task 10.7 — MetricsDashboard page

**Description:** 4 KPI cards + line chart.

**Acceptance:**
- [ ] 4 cards in grid (Users, DAU, Logs Today, Errors 24h) with last-update timestamp
- [ ] Recharts LineChart of logs/day (30d)
- [ ] Auto-refresh every 60s via React Query refetchInterval
- [ ] Loading + error states

**Verify:** Manual; cross-check numbers against direct DB queries.

**Files:** `frontend/src/app/(admin)/metrics/page.tsx`, `frontend/src/components/admin/MetricsKPICard.tsx`, `LogsPerDayChart.tsx`, `frontend/src/hooks/useAdminMetrics.ts`, `frontend/__tests__/admin/metrics.test.tsx`

**Skills:** `frontend-ui-engineering`, `test-driven-development`

---

### Task 10.8 — Log editor page

**Description:** Find log by user email + date; edit; delete.

**Acceptance:**
- [ ] Filter form (email + date)
- [ ] Results table; row → edit modal (date + note)
- [ ] Delete with confirm
- [ ] Audit visible at bottom of page
- [ ] Tests cover edit + delete paths

**Verify:** Manual: simulate a wrong log on demo user → fix via UI → verify in DB.

**Files:** `frontend/src/app/(admin)/logs/page.tsx`, `frontend/src/components/admin/LogEditor.tsx`, `AuditLogList.tsx`, `frontend/src/hooks/useAdminLogs.ts`, `frontend/__tests__/admin/log-editor.test.tsx`

**Skills:** `frontend-ui-engineering`, `test-driven-development`

---

## 5. Test plan

### Backend (in `tests/routers/test_admin.py`)
- `TestAuthz.test_user_cannot_access_admin_endpoints_returns_403` (parametrized over all admin routes)
- `TestUsers.test_list_paginates`, `test_list_search_email`, `test_suspend_sets_flag_and_audits`, `test_delete_soft_deletes_and_audits`
- `TestMetrics.test_metrics_returns_4_kpis`, `test_metrics_dau_calculation`, `test_logs_per_day_30_days`
- `TestLogs.test_filter_by_email_and_date`, `test_patch_updates_log_and_audits`, `test_delete_log_and_audits`
- `TestAudit.test_every_admin_action_creates_audit_row`

### Web (vitest + Testing Library)
- `admin-guard.test.tsx` — `redirects_non_admin_to_habits`, `allows_admin`
- `users-table.test.tsx` — `renders_users`, `suspend_calls_api`, `delete_confirms_then_calls_api`, `error_shows_toast`
- `metrics.test.tsx` — `renders_4_cards_and_chart`, `auto_refresh_pulls_new_data`
- `log-editor.test.tsx` — `filter_returns_results`, `edit_submits`, `delete_confirms`

---

## 6. Skills mapping

| Task | Primary | Secondary |
|---|---|---|
| 10.1 | `database-migrations`, `security-and-hardening` | `documentation-and-adrs` |
| 10.2 | `api-and-interface-design`, `security-and-hardening`, `test-driven-development`, `database-migrations` | `deprecation-and-migration` (soft-delete consistency) |
| 10.3 | `api-and-interface-design`, `database-migrations`, `performance-optimization`, `test-driven-development` | — |
| 10.4 | `api-and-interface-design`, `security-and-hardening`, `test-driven-development` | — |
| 10.5 | `security-and-hardening`, `frontend-ui-engineering` | `test-driven-development` |
| 10.6 | `frontend-ui-engineering`, `test-driven-development` | `code-simplification` |
| 10.7 | `frontend-ui-engineering`, `test-driven-development` | `performance-optimization` |
| 10.8 | `frontend-ui-engineering`, `test-driven-development` | — |

---

## 7. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Client-only role check bypassed | High | Server-side `redirect()` in layout PLUS server-side `require_admin` on every API endpoint — defense in depth |
| Admin accidentally deletes data permanently | High | Soft-delete + typed-confirm dialog ("Type DELETE to confirm") |
| Audit log grows unbounded | Low | Index on `created_at`; partition or prune in v2 |
| Metrics queries slow as data grows | Med | Add indexes during slice (logs/date for logs_per_day); consider materialized view if needed |
| Toast component reused inconsistently with main app | Low | Build it well now; refactor main-app spots in slice 11 polish |

---

## 8. Definition of done

- [ ] All backend + web test files GREEN
- [ ] Admin user can: list/search users, suspend, delete (soft); view metrics; edit/delete a habit log
- [ ] Non-admin redirected from `/admin/*`
- [ ] Every admin action visible in audit log
- [ ] Toast and ConfirmDialog work
- [ ] Slice committed: `feat(web+backend): admin route group, endpoints, audit logging`
- [ ] CHECKPOINT E reached: admin verified end-to-end

## 9. Estimated session count

**3–4 sessions:**
- Session 1: Tasks 10.1 + 10.2 (audit + users)
- Session 2: Task 10.3 + 10.4 (metrics + logs endpoints)
- Session 3: Tasks 10.5 + 10.6 (web layout + users page)
- Session 4: Tasks 10.7 + 10.8 (metrics + log editor)

## 10. What unblocks the next slice

- Backend complete; iOS feature-complete; web admin complete
- Slice 11 (TestFlight) has everything to ship
- Audit log proves admin actions are observable for first beta users

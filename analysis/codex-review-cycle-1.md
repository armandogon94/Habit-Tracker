# Codex Review Cycle 1

## 1. Overall Assessment

The recent pass fixed several important helper-level issues, but the app still has correctness and security problems at the API/frontend boundary. The biggest remaining risk is that completions are written using the browser's local calendar date while backend reads, streaks, "completed today", default ranges, and analytics still use the server's `date.today()`. Ownership checks are mostly present for habit IDs, and the SQL access uses SQLAlchemy expressions rather than raw SQL, but archived resources remain active through direct endpoints and several input paths remain under-validated. Test coverage is weighted toward pure helpers; risky router, auth, timezone, and UI mutation behavior is largely untested.

## 2. What Is Done Well

- Settings now fail fast for missing `DATABASE_URL` and weak `JWT_SECRET` in `backend/app/core/config.py:8-9`.
- JWT decoding requires expiry and token type in `backend/app/core/security.py:49-55`, and the access-token dependency rejects malformed UUID subjects before database lookup in `backend/app/core/deps.py:30-34`.
- Habit ownership is checked on the main habit lookup path with `Habit.id == habit_id, Habit.user_id == user_id` in `backend/app/services/habit_service.py:90-92`; I did not find a direct cross-user IDOR on active habit routes.
- `habit_logs` has a database uniqueness guard for duplicate completions via `UniqueConstraint("habit_id", "completed_date", name="uq_habit_log_date")` in `backend/app/models/habit_log.py:12-14`.
- RRULE input is intentionally narrowed to daily-only in `backend/app/schemas/habit.py:15-26`, which prevents the current daily streak implementation from silently miscounting weekly habits.
- Streak and analytics helper logic is factored into pure functions with focused tests under `backend/tests/services/`.
- Global exception handlers avoid leaking generic exception details in `backend/app/core/exceptions.py:35-40`.

## 3. Findings By Severity

### Critical

No critical issues were substantiated in this pass.

### High

#### Server-side "today" ignores the user's calendar day

**File:line:** `backend/app/services/habit_service.py:72`, `backend/app/routers/habits.py:63`, `backend/app/services/habit_service.py:223`, `frontend/src/components/habits/HabitCard.tsx:10`, `frontend/src/app/(dashboard)/habits/[id]/page.tsx:99`, `frontend/src/lib/auth.tsx:85`

**Offending code:**

```python
return build_habit_responses(habits, dates_by_habit, date.today())
```

```python
today = date.today()
```

```tsx
const today = localToday();
```

```tsx
body: JSON.stringify({ email, password }),
```

**Problem:** The frontend writes completions using the browser-local day, but the backend computes `completed_today`, current streaks, default log/calendar ranges, and analytics with the server's local day. The stored `users.timezone` field is not used in these calculations, and registration does not send a timezone at all, so new users default to `"UTC"`.

**Why this is a bug/risk:** Around UTC midnight, the API and UI disagree about what "today" means. For example, a Los Angeles user at 8 PM on 2026-06-24 logs `2026-06-24` from `localToday()`, while a UTC server already treats today as `2026-06-25`; the list/detail responses can show `completed_today=false` immediately after a successful log. For Tokyo shortly after local midnight while UTC is still the previous day, a same-day completion is a future date to the backend and is ignored by current streak calculations.

**Recommended fix:** Validate and store an IANA timezone for each user, send it during registration or infer it explicitly in the UI, and replace business-logic `date.today()` calls with `datetime.now(ZoneInfo(user.timezone)).date()`. Pass that local `today` through list, detail, analytics, logs, and calendar defaults. On the frontend, call `localToday(user.timezone)` or let the backend be the sole source of the "today" date returned in habit responses.

#### Refresh-token cookies are hard-coded as non-Secure

**File:line:** `backend/app/routers/auth.py:26-33`, `backend/app/routers/auth.py:50-57`

**Offending code:**

```python
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    samesite="lax",
    secure=False,  # True in production with HTTPS
    max_age=7 * 24 * 60 * 60,
    path="/",
)
```

**Problem:** The long-lived refresh token is always issued without the `Secure` flag.

**Why this is a bug/risk:** In production, a non-Secure refresh cookie can be sent over plain HTTP requests to the API host if such a request is ever made or forced. That turns a 7-day credential into something that can leak outside TLS. The inline comment acknowledges the production requirement, but there is no config branch enforcing it.

**Recommended fix:** Add a cookie/security settings object, default `secure=True` outside local development, and use the same cookie attributes consistently for login, register, refresh rotation, and logout. Consider the `__Host-` cookie prefix if the cookie can be host-only with `path="/"`, and make HTTPS/HSTS part of deployment verification.

### Medium

#### Protected frontend queries can race ahead of refresh and cache a 401

**File:line:** `frontend/src/app/(dashboard)/habits/page.tsx:11-13`, `frontend/src/hooks/useHabits.ts:7-11`, `frontend/src/hooks/useHabits.ts:14-19`, `frontend/src/lib/api.ts:46-48`

**Offending code:**

```tsx
const { user, loading: authLoading, logout } = useAuth();
const { data: habits, isLoading, error } = useHabits();
```

```tsx
return useQuery<Habit[]>({
  queryKey: ["habits"],
  queryFn: () => apiJson("/api/v1/habits"),
});
```

```tsx
if (res.status === 401 && accessToken) {
  const newToken = await refreshAccessToken();
```

**Problem:** Dashboard hooks start protected queries even while `AuthProvider` is still trying to refresh from the cookie. If `accessToken` is null, `apiFetch` will not attempt refresh after a 401.

**Why this is a bug/risk:** On a hard reload with only the refresh cookie present, `/api/v1/habits` can fail with 401 before the mount-time refresh succeeds. Because the query key does not include auth state and auth success does not invalidate the query, the page can remain in an error state until a manual refetch/reload. The same pattern exists for detail, calendar, and analytics queries.

**Recommended fix:** Gate protected queries with `enabled: !authLoading && !!user`, or expose an auth-ready state to the hooks. Also make `apiFetch` attempt a single refresh on 401 even when `accessToken` is null, and invalidate protected query keys after login/refresh succeeds.

#### Archived habits are still active through direct endpoints

**File:line:** `backend/app/services/habit_service.py:52-55`, `backend/app/services/habit_service.py:89-92`, `backend/app/routers/habits.py:83-208`

**Offending code:**

```python
select(Habit)
.where(Habit.user_id == user_id, Habit.archived_at.is_(None))
```

```python
select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
```

**Problem:** `list_habits` hides archived habits, but the shared `get_habit` helper does not filter `archived_at`. All direct routes use that helper, including update, log, logs, calendar, and analytics.

**Why this is a bug/risk:** After `DELETE /api/v1/habits/{id}` archives a habit, a user with the direct ID can still fetch it, update it, add completions, delete completions, and view analytics. That contradicts the soft-delete behavior implied by the list route and "Archive" UI.

**Recommended fix:** Split lookup helpers into `get_active_habit` and `get_habit_including_archived`. Use the active helper for normal read/update/log/calendar/analytics routes and reserve archived access for explicit restore/admin flows. Return 404 or 409 when a user tries to mutate an archived habit.

#### Future completion dates are accepted and inflate analytics

**File:line:** `backend/app/schemas/habit.py:68-70`, `backend/app/services/habit_service.py:123-126`, `backend/app/services/streak_service.py:48-62`, `backend/app/services/habit_service.py:212-216`

**Offending code:**

```python
class HabitLogCreate(BaseModel):
    completed_date: date
    notes: str | None = None
```

```python
log = HabitLog(
    habit_id=habit_id,
    completed_date=data.completed_date,
    notes=data.notes,
)
```

```python
days = sorted(set(completed_dates))
```

**Problem:** The API accepts any `completed_date`, including future dates. Current streak ignores dates after `today`, but longest streak and total/weekday analytics operate on all dates.

**Why this is a bug/risk:** A client can log future completions and inflate `longest_streak`, `total_completions`, `weekly_counts`, and future calendar cells. This also interacts badly with the timezone bug: a legitimate east-of-UTC same-day completion can look future to a UTC server.

**Recommended fix:** In the log route/service, validate `completed_date <= user_local_today` and decide whether past backfill is allowed and how far back. Pass an explicit `today` into longest/analytics helpers and ignore future dates there defensively. Add tests for west/east UTC boundaries and malicious future dates.

#### Calendar and log ranges are unbounded

**File:line:** `backend/app/routers/habits.py:158-175`, `backend/app/routers/habits.py:178-195`, `backend/app/services/habit_service.py:169-173`

**Offending code:**

```python
start_date: date = Query(default=None),
end_date: date = Query(default=None),
```

```python
while current <= end_date:
    days.append(CalendarDay(date=current, completed=current in completed_dates))
    current += timedelta(days=1)
```

**Problem:** Authenticated clients can request arbitrary `start_date` and `end_date` values. `get_calendar` materializes every day in memory and returns it as JSON.

**Why this is a bug/risk:** A request spanning years or the full supported `date` range can consume substantial CPU/memory and produce huge responses. The logs endpoint can similarly force broad database scans.

**Recommended fix:** Validate `start_date <= end_date` and enforce route-level max windows, such as 366 days for calendar and a bounded/paginated logs window. Return 400/422 for invalid or excessive ranges.

#### `HabitUpdate` accepts values that `HabitCreate` rejects

**File:line:** `backend/app/schemas/habit.py:29-33`, `backend/app/schemas/habit.py:41-45`, `backend/app/services/habit_service.py:96-99`

**Offending code:**

```python
name: str = Field(..., min_length=1, max_length=255)
color: str = Field(default="#3B82F6", pattern=r"^#[0-9a-fA-F]{6}$")
```

```python
class HabitUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    rrule: str | None = None
```

```python
for field, value in data.model_dump(exclude_unset=True).items():
    setattr(habit, field, value)
```

**Problem:** Update lacks the create schema's length and color-format constraints, and the service blindly applies whatever survived Pydantic's weak typing.

**Why this is a bug/risk:** A client can update a habit to an empty name or invalid CSS color that could never be created through the create endpoint. Overlong values can also turn into database errors instead of clean validation responses.

**Recommended fix:** Mirror create constraints on update fields: `name` min/max, `color` hex pattern, and any chosen description length. Consider trimming names and rejecting whitespace-only values in both create and update.

#### Archive failures are swallowed and treated as success in the UI

**File:line:** `backend/app/routers/habits.py:110-119`, `frontend/src/hooks/useHabits.ts:91-96`, `frontend/src/lib/api.ts:62-68`, `frontend/src/app/(dashboard)/habits/[id]/page.tsx:108-111`

**Offending code:**

```python
@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
```

```tsx
apiJson(`/api/v1/habits/${id}`, { method: "DELETE" }).catch(() => null),
```

```tsx
return res.json();
```

```tsx
await deleteHabit.mutateAsync(id);
router.push("/habits");
```

**Problem:** The backend correctly returns 204 with no body, but `apiJson` always parses JSON. The delete hook catches that parse failure by swallowing every error, including real 401/404/500/network failures.

**Why this is a bug/risk:** The detail page navigates back to `/habits` as if the archive succeeded even when the request failed. A user can believe data was archived when it was not.

**Recommended fix:** Use `apiFetch` for 204 endpoints and explicitly handle `res.status === 204`. Do not catch all errors in `useDeleteHabit`; only treat a known idempotent status as success if that is intentional, and surface all other failures.

#### Auth session hardening is incomplete: no rate limiting, no refresh rotation/revocation

**File:line:** `backend/app/routers/auth.py:16-24`, `backend/app/routers/auth.py:39-48`, `backend/app/routers/auth.py:63-73`, `backend/app/routers/auth.py:76-79`

**Offending code:**

```python
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
```

```python
access_token = create_access_token(str(user.id))
return TokenResponse(access_token=access_token)
```

```python
response.delete_cookie("refresh_token", path="/")
```

**Problem:** Login/register have no visible rate limit, refresh tokens are stateless JWTs with no `jti`, and logout only deletes the browser cookie. A stolen refresh token remains usable until expiry.

**Why this is a bug/risk:** Brute-force and credential-stuffing attempts are not throttled at the app layer. Refresh-token theft cannot be revoked server-side, and refresh reuse is not detectable.

**Recommended fix:** Add rate limiting on login/register/refresh, keyed by IP and account identifier. Add a refresh-token identifier, store hashed active refresh tokens server-side, rotate on refresh, and revoke on logout/password change.

### Low

#### Refresh endpoint returns 400 instead of 401 for malformed signed UUID subjects

**File:line:** `backend/app/routers/auth.py:68`, `backend/app/core/deps.py:30-34`

**Offending code:**

```python
user = await get_user_by_id(db, UUID(payload["sub"]))
```

**Problem:** The access-token dependency catches malformed UUID subjects, but `/refresh` directly calls `UUID(payload["sub"])`.

**Why this is a bug/risk:** A malformed but validly signed refresh token produces a `ValueError` handled as a generic 400, not a clean 401 "invalid refresh token". This is an edge case unless the signing secret is compromised or tests mint malformed refresh tokens, but it is inconsistent auth behavior.

**Recommended fix:** Validate `sub` in `get_refresh_token_payload` the same way `get_current_user` does, or catch `ValueError` in the refresh route and raise `HTTPException(401)`.

#### RRULE normalization is string-order sensitive

**File:line:** `backend/app/schemas/habit.py:12`, `backend/app/schemas/habit.py:15-22`

**Offending code:**

```python
_ACCEPTED_DAILY_RRULES = {"FREQ=DAILY", "FREQ=DAILY;INTERVAL=1"}
```

```python
normalized = normalized.strip().rstrip(";").strip().upper()
if normalized in _ACCEPTED_DAILY_RRULES:
    return DAILY_RRULE
```

**Problem:** The validator accepts `FREQ=DAILY;INTERVAL=1` but rejects the semantically equivalent `INTERVAL=1;FREQ=DAILY`.

**Why this is a bug/risk:** RRULE components are not meaningfully ordered for this case. If clients send otherwise valid RRULE strings in a different order, the API rejects daily habits even though the intent matches the supported subset.

**Recommended fix:** Parse the RRULE into key/value components and accept only the exact supported semantics: `FREQ=DAILY` and optional `INTERVAL=1`, with no unsupported keys.

## 4. Test-Coverage Gaps Worth Closing

- Add backend router/integration tests with a real or transactional test database for auth, habit CRUD, log/create/delete, ownership failures, duplicate logs, archived-habit behavior, and 204 delete behavior. Current backend tests are mostly pure helper/schema tests.
- Add timezone end-to-end tests for Los Angeles and Tokyo around UTC midnight, covering log creation, `completed_today`, current streak, calendar defaults, and completion-rate windows.
- Add validation tests for future completion dates, excessive calendar/log ranges, `HabitUpdate` invalid names/colors, invalid IANA timezones, and overlong login passwords.
- Add auth security tests for cookie flags under production settings, refresh-token malformed-sub handling, refresh rotation/revocation behavior once implemented, and login/register rate limits.
- Add frontend tests for auth bootstrap on hard reload with only a refresh cookie, protected query gating, delete/archive failure handling, and 204 responses.
- Add mutation/cache tests for toggling from list and detail pages across timezone boundaries so optimistic `completed_today` state matches the backend response after refetch.

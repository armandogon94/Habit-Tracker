# Codex Review Cycle 3

## 1. Overall Assessment

The cycle-1 and cycle-2 fixes are largely sound. I verified the actual source, not just the prior reports:

- Registration now accepts and validates an IANA timezone, and the web register flow sends the browser timezone:
  `backend/app/schemas/auth.py:17-36`
  ```python
  timezone: str = Field(default="UTC", max_length=64)
  ZoneInfo(value)
  ```
  `frontend/src/lib/auth.tsx:84-93`
  ```tsx
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  body: JSON.stringify({ email, password, timezone }),
  ```
- Register and login schemas reject passwords over bcrypt's 72-byte input limit:
  `backend/app/schemas/auth.py:11-13`, `backend/app/schemas/auth.py:17-25`, `backend/app/schemas/auth.py:39-46`
  ```python
  if len(value.encode("utf-8")) > _BCRYPT_MAX_BYTES:
      raise ValueError(f"password must be at most {_BCRYPT_MAX_BYTES} bytes")
  ```
- The main habit read/update/log paths now use `local_today(user.timezone)`:
  `backend/app/routers/habits.py:31`, `backend/app/routers/habits.py:64-68`, `backend/app/routers/habits.py:96-111`, `backend/app/routers/habits.py:138-142`, `backend/app/routers/habits.py:181-214`, `backend/app/routers/habits.py:227`.
- Future-dated rows are now filtered from current streaks, longest streaks when `today` is provided, list/detail/update responses, and analytics:
  `backend/app/services/streak_service.py:48-57`, `backend/app/services/habit_service.py:43-45`, `backend/app/services/habit_service.py:225-240`.
- `PUT /habits/{id}` now returns timezone-aware streaks and `completed_today`:
  `backend/app/routers/habits.py:95-111`.
- React Query cache clearing on login/register/logout is present:
  `frontend/src/lib/auth.tsx:75-80`, `frontend/src/lib/auth.tsx:99-102`, `frontend/src/lib/auth.tsx:107-115`.
- Deleting a habit now removes its detail/calendar/analytics caches:
  `frontend/src/hooks/useHabits.ts:91-104`.
- `COOKIE_SECURE` is wired into refresh-cookie creation and documented in `.env.example`:
  `backend/app/routers/auth.py:19-29`, `.env.example:20-23`.

I did not find a remaining critical or high-severity issue in the reviewed slice. The remaining findings are narrower but still real: the timezone model is not yet a single source of truth end-to-end, analytics has a UTC-created-date edge case, the password hasher still truncates if called outside the request schema boundary, toggle idempotency hides some real 404s, and refresh-token/session handling is not production-grade.

No test commands were run during this pass. I kept the review read-only except for this report because `pytest`, `vitest`, and build tooling can create cache artifacts, and the instruction allowed only `analysis/codex-review-cycle-3.md` to be written.

## 2. What Is Done Well

- The archived-habit fix is complete on normal routes. The shared lookup excludes archived rows, so read/update/log/calendar/analytics no longer operate on soft-deleted habits:
  `backend/app/services/habit_service.py:89-100`
  ```python
  select(Habit).where(
      Habit.id == habit_id,
      Habit.user_id == user_id,
      Habit.archived_at.is_(None),
  )
  ```
- The backend no longer relies on server-local `date.today()` from routers. The one remaining fallback is inside `compute_current_streak` for direct helper callers, but every habit router path I checked passes an explicit user-local `today`.
- Longest streaks are now future-filtered in the important response paths. `build_habit_responses` passes `today` to `longest_streak_from_dates`, and detail/update call `compute_longest_streak(db, habit.id, today)`.
- The delete/cache fix is materially better than cycle 2: `apiJson` handles 204, delete errors reject, and successful archive removes per-habit cached records.
- Password byte-limit validation correctly catches multibyte passwords whose character count is below 72 but UTF-8 byte count exceeds 72. The schema tests cover that edge in `backend/tests/schemas/test_auth_hardening.py:17-25`.
- The service-level analytics builders are small and testable. Future filtering is centralized in `build_analytics`, and list response construction is batched instead of N+1.

## 3. Findings By Severity

### Critical

No critical issues were substantiated.

### High

No high-severity issues were substantiated.

### Medium

#### Frontend completion dates can still diverge from the backend's stored timezone

**File:line:** `frontend/src/components/habits/HabitCard.tsx:8-18`, `frontend/src/app/(dashboard)/habits/[id]/page.tsx:70-99`, `frontend/src/app/(dashboard)/habits/[id]/page.tsx:155-160`, `backend/app/routers/habits.py:138-142`, `frontend/src/lib/auth.tsx:84-93`

**Evidence:**

```tsx
const today = localToday();
...
date: today,
```

```tsx
const { user, loading: authLoading } = useAuth();
...
const today = localToday();
```

```python
if data.completed_date > local_today(user.timezone):
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="completed_date cannot be in the future",
    )
```

**Problem:** Registration now stores the browser timezone, and the backend consistently uses `user.timezone`. But the UI still computes mutation dates from the browser's current timezone with `localToday()` and no `user.timezone` argument. That means the write path and read/validation path can split after travel, OS timezone changes, shared-device use, or existing accounts that still have `"UTC"` from before the fix.

**Why it matters:** A user registered in `America/New_York` who later opens the app in Tokyo shortly after Tokyo midnight will post the Tokyo calendar date, while the backend validates against the stored New York date. The POST can be rejected as future-dated, or `completed_today` can disagree with the date the UI just sent.

**Concrete fix:** Make the backend the source of truth for the active habit date, ideally by returning a `today` field with authenticated habit responses and using it for toggles. At minimum, pass `user.timezone` into `localToday(user.timezone)` in list/detail toggle flows. Add a timezone update/profile path or migration plan for existing `"UTC"` users who are not actually UTC.

#### Analytics completion rate uses UTC habit creation date instead of the user's local creation date

**File:line:** `backend/app/models/base.py:13-20`, `backend/app/routers/habits.py:217-227`, `backend/app/services/habit_service.py:246-256`

**Evidence:**

```python
default=lambda: datetime.now(timezone.utc)
```

```python
return await habit_service.get_analytics(db, habit, local_today(user.timezone))
```

```python
created_date = habit.created_at.date() if habit.created_at else window_start
return build_analytics(all_dates, today, created_date)
```

**Problem:** `today` is user-local, but `created_date` is derived by taking `.date()` from the UTC `created_at` timestamp. Around UTC midnight, that can be one day ahead or behind the user's local creation date.

**Why it matters:** For a Los Angeles user who creates a habit at 8 PM local on June 24, the stored UTC timestamp is already June 25. Analytics then treats the habit as created on June 25 while `today` is June 24. A same-evening completion on June 24 is ignored by `completion_rate_pct` because the effective start date is June 25. The inverse happens for users east of UTC: the denominator can include a local day before the habit existed.

**Concrete fix:** Pass the user's timezone into `get_analytics` and convert `created_at` before taking the date:

```python
created_date = habit.created_at.astimezone(ZoneInfo(user.timezone)).date()
```

Keep the UTC storage, but every calendar-day business decision should use the same user-local timezone as `local_today`.

#### Refresh tokens are stateless, non-rotating, and logout cannot revoke a stolen token

**File:line:** `backend/app/core/security.py:38-44`, `backend/app/routers/auth.py:63-79`, `backend/app/routers/auth.py:82-85`

**Evidence:**

```python
return jwt.encode(
    {"sub": user_id, "exp": expire, "type": "refresh"},
    settings.JWT_SECRET,
    algorithm=settings.JWT_ALGORITHM,
)
```

```python
payload: dict = Depends(get_refresh_token_payload)
...
access_token = create_access_token(str(user.id))
return TokenResponse(access_token=access_token)
```

```python
response.delete_cookie("refresh_token", path="/")
```

**Problem:** Refresh tokens carry no `jti`, are not stored server-side, are not rotated on `/refresh`, and logout only asks the browser to delete its cookie. Any copied refresh token remains valid until expiry.

**Why it matters:** A leaked refresh token is a 7-day bearer credential that survives logout and can mint new access tokens until expiry. This is not a cross-user authorization bug in normal API use, but it is a real production session-management gap.

**Concrete fix:** Add a refresh-token table or Redis store keyed by a hashed token id (`jti`), rotate refresh tokens on every refresh, revoke the current token on logout, and reject reused/unknown/revoked refresh tokens.

### Low

#### The public password helpers still silently truncate long passwords

**File:line:** `backend/app/core/security.py:9-26`, `backend/app/services/auth_service.py:10-25`, `backend/tests/core/test_security.py:39-54`

**Evidence:**

```python
def _bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
```

```python
user = User(email=email, password_hash=hash_password(password), timezone=tz)
```

```python
pw = "a" * 100
hashed = hash_password(pw)
assert verify_password(pw, hashed) is True
```

**Problem:** The API schemas now reject over-72-byte passwords, so the route-level cycle-2 fix is correct. But the lower-level `hash_password` and `verify_password` helpers still truncate, and `register_user`/`authenticate_user` rely on callers to have already validated the invariant.

**Why it matters:** A future mobile route, test helper, CLI, seed script, or service call can bypass the Pydantic schema and reintroduce the exact bcrypt truncation issue. The core tests still encode the old behavior as desired.

**Concrete fix:** Centralize the invariant in the password module. Make `hash_password` reject inputs over 72 UTF-8 bytes, and either make `verify_password` reject the same way or expose a clearly named internal function only for legacy hash compatibility. Update `backend/tests/core/test_security.py` so direct helper behavior cannot silently regress.

#### Toggle mutation treats every 404 as an idempotent success

**File:line:** `frontend/src/hooks/useHabits.ts:46-58`

**Evidence:**

```tsx
const res = completed
  ? await apiFetch(`/api/v1/habits/${habitId}/log/${date}`, { method: "DELETE" })
  : await apiFetch(`/api/v1/habits/${habitId}/log`, {
      method: "POST",
      body: JSON.stringify({ completed_date: date }),
    });
...
if (!res.ok && res.status !== 404 && res.status !== 409) {
```

**Problem:** The code treats `404` as success for both directions. That is only defensible for the DELETE "already absent" case. A POST 404 means the habit was not found or no longer accessible, not that the desired completed state was reached.

**Why it matters:** A stale cached habit or archived habit can be "completed" optimistically, the POST can return 404, and the UI will not surface the failure. Refetches may eventually correct the view, but the mutation contract is wrong and can hide real data-loss/conflict scenarios.

**Concrete fix:** Branch by operation. Swallow `409` only for POST-complete idempotency. Swallow `404` only for DELETE-uncomplete, and preferably only when the response detail is `"Log not found"` rather than `"Habit not found"`.

#### Production cookie safety is documented but not enforced

**File:line:** `backend/app/core/config.py:16-18`, `backend/app/routers/auth.py:19-29`, `.env.example:20-23`, `README.md:236-244`

**Evidence:**

```python
COOKIE_SECURE: bool = False
```

```python
secure=settings.COOKIE_SECURE,
```

```env
# MUST be true in any HTTPS/production deployment so the 7-day refresh token is
# never transmitted over plain HTTP.
COOKIE_SECURE=false
```

**Problem:** Cycle 2 did document `COOKIE_SECURE` in `.env.example`, and the cookie now uses the setting. The remaining issue is operational: the code still fails open, and the README environment table omits `COOKIE_SECURE`.

**Why it matters:** A production deployment that misses this setting will issue a non-Secure refresh-token cookie. The comment says it "MUST" be true, but nothing enforces that.

**Concrete fix:** Add an `APP_ENV`/`ENVIRONMENT` setting and reject startup when `APP_ENV=production` and `COOKIE_SECURE=false`. Add a config test for that rule and include `COOKIE_SECURE` in the README table.

## 4. Test-Coverage Gaps

- Add backend route/integration tests for the timezone flow, not just schema/unit tests: register with `America/Los_Angeles`, create/log near UTC midnight, assert list/detail/update/analytics agree on `completed_today`, current streak, longest streak, and future-date rejection.
- Add a regression test for analytics where `habit.created_at` UTC date differs from the user's local date. Assert completion rate uses the local creation date.
- Add frontend hook/component tests for toggles using `user.timezone` or a backend-provided `today`, including a browser timezone different from the stored profile timezone.
- Add route-level auth tests for >72-byte password rejection on `/register` and `/login`. Current coverage is schema-only, and core security tests still assert truncating behavior.
- Add concurrency tests around duplicate completions: two simultaneous POSTs for the same habit/date should produce one success and one clean 409 without leaking an unhandled `IntegrityError`.
- Add React Query auth-transition tests for logout -> login as another user and delete-habit cache removal. The implementation looks correct now, but there are no hook/component tests covering it.
- Add tests for refresh-token lifecycle once rotation/revocation exists: logout revokes, reuse is rejected, malformed `sub` remains 401, and production cookie config fails closed.
- Add frontend tests for toggle error handling: POST 404 should reject; DELETE 404 for an already-missing log may be idempotent only when the habit still exists.

## 5. Final Verdict

The reviewed slice is much healthier than cycles 1 and 2. The serious original issues around archived habits, future streak inflation, update response drift, 204 delete handling, and cross-session React Query cache leakage are fixed in the actual code.

I would not call this production-ready yet for users across timezones or for production-grade sessions. The app needs one consistent source of truth for "today", analytics must convert `created_at` into the user's timezone, and refresh-token revocation/rotation plus enforced secure-cookie configuration should be in place before treating the auth layer as production hardened.

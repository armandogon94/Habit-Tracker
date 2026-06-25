# Codex Review Cycle 2

## 1. Overall Assessment

The cycle-1 fixes are real, but not complete. The backend now has `local_today(user.timezone)` wired into most read/log paths, `get_habit` excludes archived habits, future completion creates are rejected, log/calendar ranges are bounded, `HabitUpdate` and RRULE validation were tightened, malformed refresh-token subjects return 401, `apiJson` handles 204, and the web API client retries refresh on any 401.

The biggest remaining problem is that the web app still does not persist or consistently use the user's timezone. New web users register without a timezone, so the backend stores `"UTC"` while the frontend logs dates using the browser-local day. That recreates the original "today" mismatch and also makes the new future-date rejection fail for users east of UTC. There is also still a server-side `date.today()` fallback in the habit update path.

I did not re-list cycle-1's broader auth hardening issue as a new finding below, but it remains unimplemented: auth endpoints still have no app-level rate limiting, refresh tokens are stateless/non-rotating, and logout only deletes the browser cookie.

No tests were run during this review; I kept the pass read-only except for this report.

## 2. What Is Done Well

- Archived habits are now excluded by the shared lookup used by normal routes:

  `backend/app/services/habit_service.py:89-100`

  ```python
  select(Habit).where(
      Habit.id == habit_id,
      Habit.user_id == user_id,
      Habit.archived_at.is_(None),
  )
  ```

- Most habit routes now compute default "today" from the user profile, not the server clock:

  `backend/app/routers/habits.py:31`, `backend/app/routers/habits.py:64`, `backend/app/routers/habits.py:178`, `backend/app/routers/habits.py:202`, `backend/app/routers/habits.py:223`

  ```python
  local_today(user.timezone)
  ```

- The range limiter is inclusive and correctly rejects inverted or over-wide windows:

  `backend/app/services/habit_service.py:160-167`

  ```python
  if start_date > end_date:
      raise ValueError("start_date must be on or before end_date")
  if (end_date - start_date).days + 1 > max_days:
      raise ValueError(f"date range too large (max {max_days} days)")
  ```

- `HabitUpdate` now mirrors the create constraints for name/color and validates RRULE:

  `backend/app/schemas/habit.py:44-55`

  ```python
  name: str | None = Field(default=None, min_length=1, max_length=255)
  color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
  ```

- `/refresh` now handles malformed `sub` values as a 401:

  `backend/app/routers/auth.py:68-76`

  ```python
  try:
      user_id = UUID(payload["sub"])
  except (ValueError, KeyError, TypeError):
      raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
      ) from None
  ```

- Frontend delete handling no longer parses JSON from 204 responses and no longer swallows all archive failures:

  `frontend/src/lib/api.ts:63-73`, `frontend/src/hooks/useHabits.ts:91-98`

  ```ts
  if (res.status === 204) {
    return undefined as T;
  }
  ```

## 3. Findings By Severity

### Critical

No critical issues were substantiated in this pass.

### High

#### Web registration still stores UTC, so the timezone-aware backend is wrong for normal web users

**File:line:** `backend/app/schemas/auth.py:4-7`, `backend/app/services/auth_service.py:10-15`, `frontend/src/lib/auth.tsx:80-86`, `frontend/src/components/habits/HabitCard.tsx:8-17`, `frontend/src/app/(dashboard)/habits/[id]/page.tsx:99`, `backend/app/routers/habits.py:134-138`, `backend/app/services/time_service.py:15-21`

**Evidence:**

```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    timezone: str = "UTC"
```

```python
async def register_user(db: AsyncSession, email: str, password: str, tz: str = "UTC") -> User:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    user = User(email=email, password_hash=hash_password(password), timezone=tz)
```

```tsx
body: JSON.stringify({ email, password }),
```

```tsx
const today = localToday();

function handleToggle(e: React.MouseEvent) {
  e.preventDefault();
  e.stopPropagation();
  toggle.mutate({
    habitId: habit.id,
    date: today,
    completed: habit.completed_today,
  });
}
```

```python
if data.completed_date > local_today(user.timezone):
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="completed_date cannot be in the future",
    )
```

**Problem:** The backend fix depends on `user.timezone`, but the web registration flow never sends one, so new web users keep the schema default `"UTC"`. At the same time, the UI still logs dates from `localToday()` with no explicit timezone, meaning the browser's local date can differ from the backend's stored UTC date. The server also accepts arbitrary timezone strings and silently falls back to UTC on bad stored input.

**Why this is a bug/risk:** This preserves the original timezone bug for the main web flow. A Los Angeles user after UTC midnight can log the browser date for June 24 while the backend considers "today" June 25, so `completed_today` and streaks remain wrong. A Tokyo user shortly after local midnight can send June 25 while the backend-stored UTC date is still June 24, and the new future-date check rejects a legitimate local completion with 422.

**Concrete fix:** Validate `RegisterRequest.timezone` as an IANA zone server-side, add a max length matching the database column, and reject invalid values instead of falling back for newly submitted input. Have the web register flow send `Intl.DateTimeFormat().resolvedOptions().timeZone`, and have habit toggles use `user.timezone` or, better, a backend-provided `today` value so the read and write paths share one calendar source. Add a profile migration/backfill path for existing `"UTC"` users who are not actually UTC.

#### Protected React Query caches can leak one user's habits into the next session

**File:line:** `frontend/src/components/providers.tsx:8-14`, `frontend/src/hooks/useHabits.ts:7-18`, `frontend/src/hooks/useHabits.ts:101-113`, `frontend/src/lib/auth.tsx:61-78`, `frontend/src/lib/auth.tsx:99-106`

**Evidence:**

```tsx
new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})
```

```tsx
queryKey: ["habits"],
```

```tsx
queryKey: ["habit", id],
```

```tsx
const logout = useCallback(async () => {
  await fetch(`${API_URL}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  setAccessToken(null);
  setUser(null);
}, []);
```

**Problem:** Protected query keys are not scoped by user id, and auth transitions do not clear the TanStack Query cache. Because queries are considered fresh for 30 seconds, a logout followed by a different user's login on the same browser can reuse the previous user's cached `["habits"]`, `["habit", id]`, `["calendar", id]`, or `["analytics", id]` data before any network fetch runs.

**Why this is a bug/risk:** This is a client-side privacy leak. User B can briefly see User A's habit names, descriptions, colors, streaks, calendar, or analytics on a shared device if User B signs in within the stale window. The server authorization checks still protect the API, but the frontend has already retained and rendered protected data from the prior principal.

**Concrete fix:** Clear or remove all protected queries on logout and before/after successful login/register. Also include `user.id` in protected query keys, or create a new `QueryClient` per authenticated session. Invalidate protected keys after auth refresh/login succeeds so stale anonymous or prior-user errors/data cannot survive the session boundary.

### Medium

#### The habit update response still uses server `date.today()` and defaults `completed_today` to false

**File:line:** `backend/app/routers/habits.py:84-108`, `backend/app/services/streak_service.py:65-76`, `backend/app/schemas/habit.py:58-68`

**Evidence:**

```python
habit = await habit_service.update_habit(db, habit, data)
current = await compute_current_streak(db, habit.id)
longest = await compute_longest_streak(db, habit.id)
```

```python
async def compute_current_streak(
    db: AsyncSession, habit_id: UUID, today: date | None = None
) -> int:
    if today is None:
        today = date.today()
```

```python
completed_today: bool = False
```

**Problem:** All the main read paths were moved to `local_today(user.timezone)`, but `PUT /api/v1/habits/{id}` still calls `compute_current_streak` without passing `today`. That helper falls back to the server calendar date. The update response also omits `completed_today`, so Pydantic returns the default `False` even if the habit is completed on the user's local day.

**Why this is a bug/risk:** Any frontend or API client that uses the update response can regress to the old timezone behavior immediately after editing a habit. Around UTC midnight, the same habit can report one streak/completion state from `GET /habits/{id}` and a different state from `PUT /habits/{id}`.

**Concrete fix:** Compute `today = local_today(user.timezone)` in the update route, pass it to `compute_current_streak`, query today's log as the get route does, and populate `completed_today`. Consider removing the optional fallback from `compute_current_streak` so business code must pass an explicit date.

#### Future-dated rows still inflate list/detail longest streaks

**File:line:** `backend/app/services/habit_service.py:25-48`, `backend/app/services/streak_service.py:79-82`, `backend/app/services/habit_service.py:219-240`

**Evidence:**

```python
longest_streak=longest_streak_from_dates(dates),
```

```python
async def compute_longest_streak(db: AsyncSession, habit_id: UUID) -> int:
    result = await db.execute(
        select(HabitLog.completed_date).where(HabitLog.habit_id == habit_id)
    )
    return longest_streak_from_dates(row[0] for row in result.all())
```

```python
# Ignore any future-dated completion (the API also rejects them) so totals,
# weekday distribution and longest streak cannot be inflated.
all_dates = [d for d in completed_dates if d <= today]
```

```python
return HabitAnalytics(
    total_completions=len(all_dates),
    completion_rate=completion_rate_pct(all_dates, today, created_date),
    current_streak=current_streak_from_dates(all_dates, today),
    longest_streak=longest_streak_from_dates(all_dates),
    best_day=best_day,
    weekly_counts=weekly,
)
```

**Problem:** Analytics defensively filters out dates after `today`, but list/detail longest-streak paths still compute over every stored log date. The API now rejects newly-created future logs, but rows created before the fix, imported rows, or manually inserted rows still affect `GET /habits` and `GET /habits/{id}`.

**Why this is a bug/risk:** The API can return inconsistent numbers for the same habit: analytics says one longest streak, while list/detail show an inflated value that includes future completions. This is especially relevant because cycle 1 explicitly allowed future logs before this fix; existing production data may already contain them.

**Concrete fix:** Make longest-streak computation accept `today` and filter `d <= today` everywhere, including `build_habit_responses` and `compute_longest_streak`. Add a cleanup migration or admin repair for future-dated rows that were accepted before the validator existed.

#### Password handling silently truncates long inputs at bcrypt's 72-byte boundary

**File:line:** `backend/app/core/security.py:9-26`, `backend/app/schemas/auth.py:4-12`, `backend/tests/core/test_security.py:39-54`

**Evidence:**

```python
_BCRYPT_MAX_BYTES = 72

def _bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
```

```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    timezone: str = "UTC"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

```python
pw = "a" * 100
hashed = hash_password(pw)
assert verify_password(pw, hashed) is True
```

**Problem:** The code avoids bcrypt crashes by truncating every password to 72 bytes before hashing/checking. Registration accepts up to 128 characters, and login has no schema max at all.

**Why this is a bug/risk:** Two different passwords with the same first 72 UTF-8 bytes authenticate as the same password. Users who choose long passphrases believe the suffix matters, but it does not. The unbounded login schema also leaves very large password bodies to be parsed/encoded before truncation.

**Concrete fix:** Either reject passwords whose UTF-8 encoding exceeds bcrypt's 72-byte limit with a clear validation error on both register and login, or switch to a safe prehash/modern password-hashing scheme such as Argon2id. Do not silently discard suffix bytes.

#### The Secure cookie fix is config-driven but still fails open and is undocumented

**File:line:** `backend/app/core/config.py:16-18`, `backend/app/routers/auth.py:19-29`, `.env.example:17-25`, `.env.example:35-38`

**Evidence:**

```python
# Secure flag for the refresh-token cookie. False for local HTTP dev; MUST be
# set true (COOKIE_SECURE=true) in any HTTPS/production deployment.
COOKIE_SECURE: bool = False
```

```python
response.set_cookie(
    key="refresh_token",
    value=token,
    httponly=True,
    samesite="lax",
    secure=settings.COOKIE_SECURE,
    max_age=REFRESH_COOKIE_MAX_AGE,
    path="/",
)
```

```env
JWT_SECRET=your-secret-key-here-min-32-chars-required
REDIS_URL=redis://localhost:6379/2
LOG_LEVEL=info
FRONTEND_PORT=3020
NEXT_PUBLIC_API_URL=http://localhost:8020
```

**Problem:** The cookie flag is now configurable, but the default remains `False` and the env template does not mention `COOKIE_SECURE`. A production deployment built from the provided template will keep issuing non-Secure refresh-token cookies unless the operator discovers the undocumented variable.

**Why this is a bug/risk:** The long-lived refresh token can be sent over plain HTTP if any request hits the API host without HTTPS enforcement. This was the original security risk; the fix reduces hard-coding but still fails open.

**Concrete fix:** Make the secure flag default to safe behavior outside explicit local development. For example, add an `APP_ENV`/`ENVIRONMENT` setting and require `COOKIE_SECURE=true` when not local, or make `COOKIE_SECURE` required in production. Document it in `.env.example` and README, and add tests for both local and production settings.

### Low

#### Archive only invalidates the list cache, leaving stale archived detail data reachable

**File:line:** `frontend/src/hooks/useHabits.ts:14-18`, `frontend/src/hooks/useHabits.ts:91-98`, `frontend/src/hooks/useHabits.ts:101-113`, `frontend/src/app/(dashboard)/habits/[id]/page.tsx:108-115`, `backend/app/services/habit_service.py:89-100`

**Evidence:**

```tsx
export function useDeleteHabit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiJson(`/api/v1/habits/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["habits"] }),
  });
}
```

```tsx
queryKey: ["habit", id],
```

```tsx
queryKey: ["calendar", habitId],
```

```tsx
queryKey: ["analytics", habitId],
```

**Problem:** The backend now correctly treats archived habits as gone, but the frontend keeps any cached detail/calendar/analytics entries after a successful archive. The detail page pushes to `/habits`, but pressing Back within the fresh cache window can show an archived habit from memory even though the API would now return 404.

**Why this is a bug/risk:** This is not a server authorization bypass, but it creates a stale UI path where a user sees and can interact with a habit that was just archived. Follow-up toggles will then fail or be treated idempotently depending on status, which makes the archive behavior look inconsistent.

**Concrete fix:** On delete success, remove or invalidate `["habit", id]`, `["calendar", id]`, and `["analytics", id]` in addition to `["habits"]`. Consider optimistically removing the deleted habit from the list cache as well.

## 4. Test-Coverage Gaps

- Add backend route/integration tests for the full timezone flow: registration stores a non-UTC IANA timezone, invalid/overlong timezone input is rejected, LA/Tokyo UTC-boundary completions are accepted or rejected correctly, and `completed_today` matches the user's local date.
- Add a regression test for `PUT /api/v1/habits/{id}` proving it uses `local_today(user.timezone)` and returns correct `completed_today`.
- Add tests with pre-existing future-dated logs to ensure list, detail, and analytics all filter future dates consistently.
- Add React Query/auth tests for logout -> login as another user, asserting protected query caches are cleared or scoped by user id.
- Add frontend tests for archive success invalidating/removing detail, calendar, and analytics caches.
- Add settings/cookie tests that fail production-like configuration when `COOKIE_SECURE` is false or undocumented.
- Add password validation tests for >72-byte passwords on both register and login, matching the chosen reject/prehash policy.
- Add backend router tests for archived-habit 404 behavior, future-date 422, range-bound 422, duplicate-log 409, malformed refresh-token subject 401, and concurrent duplicate completion attempts.

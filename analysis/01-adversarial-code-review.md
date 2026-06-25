# Adversarial Code Review — Confirmed Findings

> Habit Tracker · throttled Opus review fleet (87 agents, ~4.9M tokens). Each finding survived an independent skeptic agent that tried to refute it.

> Raw: 77 · **Confirmed: 62** · Refuted: 15

**Severity (confirmed):** critical=3, high=18, medium=32, low=9

---

## [CRITICAL] Hardcoded JWT signing secret is the live runtime value — anyone can forge tokens for any user

- **File:** `backend/app/core/config.py:6`
- **Category:** backend-auth / hardcoded secret · **Dimension:** backend-auth · **Verifier confidence:** high

JWT_SECRET defaults to a fixed, source-committed string and there is no startup guard requiring an override. I confirmed at runtime that this default is what the app actually loads: no .env.local exists at the path config.py points to (env_file='../.env.local'), and Settings() resolves JWT_SECRET to 'dev-secret-key-change-in-production-min-32-chars'. With HS256 (symmetric), this same string both signs and verifies, so any attacker who reads this public repo can mint a valid token for ANY user id (sub) — full account takeover of every account, including the planned admin/role-gated routes. The .env.example ships another guessable placeholder ('your-secret-key-here-min-32-chars-required') and the handoff lists 'password to env' as not-yet-done, so there is no evidence a strong secret is injected anywhere.

**Evidence:**

~~~
JWT_SECRET: str = "dev-secret-key-change-in-production-min-32-chars"
# Runtime check (no .env.local present):
#   settings.JWT_SECRET == 'dev-secret-key-change-in-production-min-32-chars'  -> True
~~~

**Fix:**

~~~
Make the secret mandatory and fail fast if absent or default:

class Settings(BaseSettings):
    JWT_SECRET: str  # no default — required

    @field_validator("JWT_SECRET")
    @classmethod
    def _strong_secret(cls, v: str) -> str:
        if not v or len(v) < 32 or v.startswith("dev-secret"):
            raise ValueError("JWT_SECRET must be set to a strong (>=32 char) non-default value")
        return v

Generate per-environment via `openssl rand -hex 32`, inject through the environment/secret manager, and never commit it. Rotate the currently-exposed secret immediately.
~~~

---

## [CRITICAL] Hardcoded default JWT_SECRET with no startup guard collapses the entire per-user ownership model (token forgery → full IDOR)

- **File:** `backend/app/core/config.py:6`
- **Category:** authz-idor / broken-access-control · **Dimension:** backend-authz-idor · **Verifier confidence:** high

Every habit/log endpoint enforces ownership solely through `get_habit(db, habit_id, user.id)` where `user.id` is derived from the JWT `sub` claim in `get_current_user` (backend/app/core/deps.py:26-35). That ownership filter is only as strong as the JWT signing key. `JWT_SECRET` defaults to the literal, repo-public constant "dev-secret-key-change-in-production-min-32-chars" and is loaded from `../.env.local`, a file that does not exist anywhere in the repo (verified: `ls .env.local backend/.env.local` -> No such file). There is no `field_validator`/`model_validator`/assert that rejects the default secret at startup (verified via grep). The only runnable stack, docker-compose.dev.yml:38, hardcodes another public constant `dev-secret-change-in-production-min32chars`. Because HS256 is symmetric, anyone who reads this repo can mint `jwt.encode({"sub": "<victim_user_id>", "type": "access", "exp": <future>}, '<known secret>', 'HS256')` and pass `get_current_user`. With a forged token, `Habit.user_id == user.id` matches the attacker-chosen victim, so an attacker can read, edit (PUT), delete (archive), log completions, delete logs, and pull analytics for ANY user's habits. This is a complete authorization bypass — the worst-case IDOR — and it is reachable in every configuration shipped in the repo.

**Evidence:**

~~~
config.py:6  JWT_SECRET: str = "dev-secret-key-change-in-production-min-32-chars"
config.py:14 model_config = {"env_file": "../.env.local", "extra": "ignore"}   # ../.env.local absent in repo
docker-compose.dev.yml:38  JWT_SECRET: dev-secret-change-in-production-min32chars
security.py:35-40  jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])  # only signature check, key is the weak default
deps.py:26-31  user_id = payload.get("sub") ... select(User).where(User.id == UUID(user_id))  # trusts forgeable sub
~~~

**Fix:**

~~~
Remove the insecure default and fail closed if the secret is missing or known-weak. In config.py:

    from pydantic import field_validator
    class Settings(BaseSettings):
        JWT_SECRET: str  # no default -> startup error if unset
        @field_validator("JWT_SECRET")
        @classmethod
        def _strong_secret(cls, v: str) -> str:
            weak = {"dev-secret-key-change-in-production-min-32-chars",
                    "dev-secret-change-in-production-min32chars",
                    "your-secret-key-here-min-32-chars-required"}
            if v in weak or len(v) < 32:
                raise ValueError("JWT_SECRET must be set to a strong (>=32 char) random value")
            return v

Generate per-environment secrets (`openssl rand -hex 32`), inject via real secret management, and never commit them. Same treatment for the Postgres password default on config.py:5.
~~~

---

## [CRITICAL] Hardcoded fallback secrets (JWT signing key + DB password) ship as Settings defaults — auth forgeable when env is unset

- **File:** `backend/app/core/config.py:5-6`
- **Category:** security/secrets · **Dimension:** backend-config-secrets · **Verifier confidence:** high

Settings declares fully functional default values for the two most sensitive config items. JWT_SECRET defaults to the literal string "dev-secret-key-change-in-production-min-32-chars" and DATABASE_URL embeds a real-looking password. Because pydantic-settings treats these as valid values, `settings = Settings()` (config.py:17) succeeds with NO environment configured and the app boots fully functional on the fallback secret. This secret is committed to the repo and therefore public. Any attacker who reads the source (or guesses this well-known placeholder) can forge a valid access token for ANY user id: the token is signed HS256 with a key they know. create_access_token (security.py:17-23) and decode_token (security.py:37) both read `settings.JWT_SECRET`, so a forged `{"sub": "<victim uuid>", "type": "access", "exp": <future>}` passes get_current_user (deps.py:22-31) and grants full account takeover. There is no runtime guard that the deployed secret differs from this default, so a misconfigured deploy (missing env) silently runs with the public key instead of refusing to start.

**Evidence:**

~~~
DATABASE_URL: str = "postgresql+asyncpg://postgres:changeme_secure_password@localhost:5432/habits_db"
JWT_SECRET: str = "dev-secret-key-change-in-production-min-32-chars"
~~~

**Fix:**

~~~
Make the sensitive fields required (no default) and validate them at construction so the process refuses to start without real values:

```python
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE = {
    "dev-secret-key-change-in-production-min-32-chars",
    "dev-secret-change-in-production-min32chars",
    "your-secret-key-here-min-32-chars-required",
}

class Settings(BaseSettings):
    DATABASE_URL: str          # no default -> required
    JWT_SECRET: str            # no default -> required
    ENVIRONMENT: str = "development"
    ...
    @field_validator("JWT_SECRET")
    @classmethod
    def _check_secret(cls, v: str) -> str:
        if len(v) < 32 or v in _INSECURE:
            raise ValueError("JWT_SECRET must be set to a strong, non-default value (>=32 chars)")
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```
With required fields, `Settings()` raises pydantic ValidationError at import time if JWT_SECRET/DATABASE_URL are missing — fail-closed instead of silently using a public key. Generate real secrets with `openssl rand -hex 32` and inject via env only.
~~~

---

## [HIGH] No rate limiting on /auth/* — unlimited credential brute-force and account enumeration

- **File:** `backend/app/routers/auth.py:39`
- **Category:** backend-auth / brute force · **Dimension:** backend-auth · **Verifier confidence:** high

The /login, /register, and /refresh endpoints have no rate limiting, throttling, CAPTCHA, or account lockout. I grepped the entire backend (app + pyproject + uv.lock) for slowapi/limiter/ratelimit/throttle and found nothing — it is simply not implemented, and the handoff explicitly lists 'Rate limiting on /auth/* → Slice 01' as outstanding. An attacker can run unlimited password-guessing against /login (each attempt returns a clean 401), enumerate which emails are registered via /register (409 'Email already registered' vs 201), and hammer /refresh. Combined with the timing oracle below, account discovery and credential stuffing are unconstrained.

**Evidence:**

~~~
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
# grep for slowapi|limiter|ratelimit|throttle across backend/ -> (no matches)
~~~

**Fix:**

~~~
Add slowapi (already cited in the handoff references):

from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest, ...): ...

Apply tight limits to /login, /register, /refresh (e.g. 5/min/IP plus a per-account counter), back it with the already-configured Redis instance, and add progressive lockout after N failures per account.
~~~

---

## [HIGH] Logout cannot revoke tokens and refresh tokens are never rotated — stolen tokens stay valid for the full 7 days

- **File:** `backend/app/routers/auth.py:76`
- **Category:** backend-auth / session revocation · **Dimension:** backend-auth · **Verifier confidence:** high

The architecture (CLAUDE.md) promises a Redis whitelist for 'immediate revocation', but Redis is not wired: I grepped the whole backend and Redis is referenced only as an unused config string (config.py:10), and the handoff states 'Redis token whitelist NOT YET WIRED'. Consequences: (1) /logout only calls response.delete_cookie — it clears the client cookie but the signed refresh JWT remains cryptographically valid until its 7-day exp, so an attacker who already captured it can keep calling /refresh to mint fresh access tokens after the user 'logged out'. (2) /refresh issues a new access token but never rotates the refresh token (no new cookie, no old-token invalidation), so there is no refresh-token-reuse detection — a single stolen refresh token is a 7-day skeleton key. There is no server-side session state to revoke at all.

**Evidence:**

~~~
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}

@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: dict = Depends(get_refresh_token_payload), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(db, UUID(payload["sub"]))
    ...
    access_token = create_access_token(str(user.id))
    return TokenResponse(access_token=access_token)  # refresh token NOT rotated/whitelisted
~~~

**Fix:**

~~~
Wire the Redis whitelist as designed and rotate on every refresh: (a) embed a unique jti in each refresh token; (b) on login/register store the jti in Redis with the token TTL; (c) in get_refresh_token_payload verify the jti is present in Redis (reject if absent = revoked); (d) on /refresh, delete the old jti and issue+store a new refresh token (rotation), setting a fresh cookie; (e) on /logout, delete the jti from Redis so the token is dead server-side. Detect reuse: if a /refresh presents a jti already consumed, revoke the whole session family.
~~~

---

## [HIGH] Unbounded date range in calendar/log endpoints enables CPU+memory DoS

- **File:** `backend/app/services/habit_service.py:155`
- **Category:** unvalidated-input · **Dimension:** backend-injection-validation · **Verifier confidence:** high

get_calendar materializes one CalendarDay object per day across a fully caller-controlled range with no upper bound: `current = start_date; while current <= end_date: days.append(CalendarDay(...)); current += timedelta(days=1)`. The router (habits.py:178-195) accepts start_date/end_date as raw Query params with default=None and only fills defaults when absent -- it never validates that start_date <= end_date, nor that the span is bounded. Python's datetime.date ranges from year 1 to 9999, so `GET /habits/{id}/calendar?start_date=0001-01-01&end_date=9999-12-31` drives ~3,652,059 loop iterations, allocating ~3.6M Pydantic instances and serializing them into one JSON response -- pegging a CPU core and exhausting memory per request. A few concurrent requests take the worker down. get_logs (habits.py:158-175) shares the same unbounded-range surface feeding the DB BETWEEN. Auth is required, but any logged-in user (free /register) can fire this; it is an authenticated O(range) amplification.

**Evidence:**

~~~
habit_service.py:155-160 ->
current = start_date
while current <= end_date:
    days.append(CalendarDay(date=current, completed=current in completed_dates))
    current += timedelta(days=1)
Router has no guard: habits.py:181-182 `start_date: date = Query(default=None)` / `end_date: date = Query(default=None)`; only `if not end_date`/`if not start_date` defaulting follows.
~~~

**Fix:**

~~~
Bound and order-check the range at the router/service boundary before iterating:

```python
MAX_RANGE_DAYS = 366
if start_date > end_date:
    raise HTTPException(422, "start_date must be <= end_date")
if (end_date - start_date).days > MAX_RANGE_DAYS:
    raise HTTPException(422, f"range exceeds {MAX_RANGE_DAYS} days")
```
Apply to both /calendar and /logs. Consider returning only completed days plus window metadata rather than densifying every calendar day server-side.
~~~

---

## [HIGH] N+1 query explosion in list_habits — 3 extra round-trips per habit, all unbounded

- **File:** `backend/app/services/habit_service.py:21-58`
- **Category:** performance/N+1 · **Dimension:** backend-data-layer · **Verifier confidence:** high

list_habits loads all non-archived habits (1 query), then loops over them and per habit issues: compute_current_streak (1 query, streak_service.py:14), compute_longest_streak (1 query, streak_service.py:46), and a 'completed today' SELECT (1 query, habit_service.py:36-40). That is 1 + 3N queries for the user's primary dashboard endpoint (GET /api/v1/habits). A user with 30 habits triggers 91 sequential awaited DB round-trips on every dashboard load — each awaited serially (no asyncio.gather), so latency is the sum of all of them. compute_longest_streak additionally pulls EVERY historical completed_date for the habit into Python on each call. get_analytics (lines 163-202) similarly issues ~5 separate queries plus two full-table reads of completed_date for the same habit (get_analytics calls compute_current_streak, compute_longest_streak, get_logs, a count, AND an all-dates SELECT). This will not scale and makes the hottest endpoint O(N) DB chatter.

**Evidence:**

~~~
for habit in habits:
    current = await compute_current_streak(db, habit.id, today)
    longest = await compute_longest_streak(db, habit.id)
    log_result = await db.execute(
        select(HabitLog).where(
            HabitLog.habit_id == habit.id, HabitLog.completed_date == today
        )
    )
    completed_today = log_result.scalar_one_or_none() is not None
~~~

**Fix:**

~~~
Fetch all logs for the user's habits in ONE query (join HabitLog to Habit on user_id, or `WHERE habit_id IN (:ids)`), group dates by habit_id in Python, and compute current/longest streak and completed_today from the in-memory per-habit date lists — eliminating the 3N round-trips. e.g. `rows = await db.execute(select(HabitLog.habit_id, HabitLog.completed_date).join(Habit).where(Habit.user_id==user_id, Habit.archived_at.is_(None)))` then build `dates_by_habit: dict[UUID, list[date]]` and reuse pure-Python streak helpers. In get_analytics, reuse a single all-dates fetch for total/streaks/weekly/best-day instead of 5 queries.
~~~

---

## [HIGH] RRULE schedule is never applied — streak algorithm hardcodes a daily assumption, breaking weekday/custom habits

- **File:** `backend/app/services/streak_service.py:35`
- **Category:** correctness · **Dimension:** backend-streak-correctness · **Verifier confidence:** high

The streak engine treats every habit as if it must be completed every single calendar day. `compute_current_streak` walks backward subtracting exactly `timedelta(days=1)` each step, and `compute_longest_streak` only counts a continuation when `(dates[i] - dates[i-1]).days == 1`. The habit's `rrule` field (e.g. `FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR` or `FREQ=WEEKLY;BYDAY=MO,WE,FR`, documented as a first-class feature in CLAUDE.md and stored on `Habit.rrule`) is never parsed. A grep across `backend/app/**` shows `rrule` appears ONLY as a pass-through into response objects (`rrule=habit.rrule`) and is never fed to `dateutil.rrule` or any scheduling logic. Consequence: a user with a Mon/Wed/Fri habit who completes it perfectly on schedule gets `current_streak = 1` every time, because Tuesday and Thursday have no log and the backward walk immediately breaks at the first missing day. A weekday-only habit completed every weekday shows a streak that resets to 1 every Monday (the Sat/Sun gap breaks it). The core value proposition of the app — streaks — is silently wrong for every non-daily habit.

**Evidence:**

~~~
streak_service.py lines 35-40:
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)   # <-- always -1 day, ignores rrule
        else:
            break
and lines 59-64:
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:   # <-- only consecutive calendar days count
            current += 1
The function signature `async def compute_current_streak(db, habit_id, today=None)` does not even receive the habit or its rrule. Grep confirms no `dateutil`, `rrule`, `FREQ`, or `BYDAY` token exists anywhere under backend/app/.
~~~

**Fix:**

~~~
Make the streak walk schedule-aware by iterating over the habit's expected occurrence dates, not raw calendar days. Load the habit, parse its rrule, and step over scheduled dates only:

from dateutil.rrule import rrulestr

async def compute_current_streak(db, habit, today):
    # fetch completed dates as a set
    rows = await db.execute(select(HabitLog.completed_date).where(HabitLog.habit_id==habit.id, HabitLog.completed_date<=today))
    done = {r[0] for r in rows.all()}
    if not done:
        return 0
    rule = rrulestr(habit.rrule, dtstart=datetime.combine(habit.created_at.date(), time.min))
    # build the list of scheduled occurrence dates up to today, newest first
    scheduled = sorted({occ.date() for occ in rule.between(habit.created_at, datetime.combine(today, time.max), inc=True)}, reverse=True)
    streak = 0
    started = False
    for d in scheduled:
        if d == today and d not in done:
            continue  # today not yet due-complete, don't break
        if d in done:
            streak += 1
            started = True
        elif started or d < today:
            break
    return streak

Apply the same occurrence-based iteration to compute_longest_streak (consecutive *scheduled* occurrences, not days==1). Add unit tests for FREQ=DAILY, weekday-only, and FREQ=WEEKLY;BYDAY=MO,WE,FR.
~~~

---

## [HIGH] User timezone is stored but never used — all streak/'completed today' boundaries use server UTC instead of user's local midnight

- **File:** `backend/app/services/streak_service.py:12`
- **Category:** correctness · **Dimension:** backend-streak-correctness · **Verifier confidence:** medium

Every notion of 'today' in the backend is `date.today()`, which returns the *server process* local date. The backend container has no TZ configured (confirmed: `grep TZ= docker-compose*.yml backend/Dockerfile` returns nothing), so Python uses UTC. The `User.timezone` column exists (IANA string like `America/Los_Angeles`, set at registration in auth_service.py and stored in the DB) and CLAUDE.md explicitly states 'Daily reset determined by user's midnight, not UTC midnight' — but `user.timezone` is never read by any streak, calendar, or analytics code (grep shows it is only echoed back in auth responses). Concretely, for a user in `America/Los_Angeles` (UTC-8): between 4:00pm and midnight local time, UTC has already rolled to the next calendar day. So `date.today()` on the server is already 'tomorrow' relative to the user. The 'completed today' lookup in `list_habits`/`get_habit` queries `completed_date == date.today()` (a UTC date), so a habit the user completed at 5pm their time (and which the frontend logged under the user's perceived date) will show as NOT completed today, the toggle renders un-checked, and the streak's anchor (`dates[0] == today` vs `today-1`) is evaluated against the wrong day. This produces phantom broken streaks and lets users double-log across the artificial UTC boundary. This is the single highest-impact correctness defect for any user not in UTC.

**Evidence:**

~~~
streak_service.py:10-12:
async def compute_current_streak(db, habit_id, today=None):
    if today is None:
        today = date.today()   # server-local (UTC in container), NOT user.timezone
habit_service.py:29 `today = date.today()`, :171 `today = date.today()`; habits.py:63,171,191 all `date.today()`. `user.timezone` never appears in any of these modules. CLAUDE.md: 'Daily reset determined by user's midnight, not UTC midnight.' Container has no TZ env (grep returned nothing).
~~~

**Fix:**

~~~
Compute 'today' in the user's timezone and thread it through every streak/calendar/analytics call:

from datetime import datetime
from zoneinfo import ZoneInfo

def user_today(user) -> date:
    return datetime.now(ZoneInfo(user.timezone or 'UTC')).date()

Then in routers/services pass `today=user_today(user)` instead of calling `date.today()`. Update list_habits/get_analytics signatures to accept the User (or its tz) so the 'completed_today' query (`completed_date == user_today(user)`) and streak anchor use the user's local date. Validate the IANA string at registration (reject values ZoneInfo can't load) so this never throws at request time.
~~~

---

## [HIGH] Frontend logs/checks completions against the UTC date, diverging from any user not in UTC

- **File:** `frontend/src/components/habits/HabitCard.tsx:9`
- **Category:** correctness · **Dimension:** backend-streak-correctness · **Verifier confidence:** high

The web client derives 'today' with `new Date().toISOString().split('T')[0]`. `toISOString()` always converts to UTC, so for a user west of UTC in the evening (or east of UTC after their local midnight) the date string is the wrong calendar day relative to what the user sees on their clock. This date is sent verbatim as `completed_date` when toggling a habit (`useToggleHabit` → `body: JSON.stringify({ completed_date: date })`) and is used to DELETE the log (`/log/${date}`). Because the backend independently uses its own UTC `date.today()` for the 'completed_today' flag and streak anchor, the two can disagree, and the user can be tricked into creating a log under a date they never intended (e.g. at 6pm Pacific the toggle writes a log dated 'tomorrow'). The toggle button then shows the opposite state from reality, and undo targets the wrong date.

**Evidence:**

~~~
HabitCard.tsx:9 `const today = new Date().toISOString().split("T")[0];` then toggle.mutate({ habitId, date: today, completed: habit.completed_today }). useHabits.ts:53 `body: JSON.stringify({ completed_date: date })` and :48 `/log/${date}` DELETE. Same UTC pattern at habits/[id]/page.tsx:98 `const today = new Date().toISOString().split("T")[0];`.
~~~

**Fix:**

~~~
Build the local calendar date without UTC conversion, ideally in the user's stored IANA zone so it matches the backend:

// local-date string YYYY-MM-DD using the browser/user tz
function localToday(tz?: string) {
  const fmt = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year:'numeric', month:'2-digit', day:'2-digit' });
  return fmt.format(new Date()); // en-CA yields YYYY-MM-DD
}
Use `localToday(user.timezone)` everywhere `new Date().toISOString().split('T')[0]` appears. Better, have the server resolve 'today' from `user.timezone` and return `completed_today`/the canonical today so client and server can never disagree.
~~~

---

## [HIGH] 30-day completion rate divides by a hardcoded 30, ignoring habit age and schedule — yields impossible/garbage percentages

- **File:** `backend/app/services/habit_service.py:178`
- **Category:** correctness · **Dimension:** backend-streak-correctness · **Verifier confidence:** high

`get_analytics` computes `rate = (len(recent_logs) / 30) * 100`. This is wrong in three ways. (1) Habit age: a habit created 3 days ago that was completed all 3 days reports 3/30 = 10% completion, badly under-reporting and demoralizing the user. (2) Schedule: for a weekday-only or FREQ=WEEKLY;BYDAY=MO,WE,FR habit, the denominator should be the number of *scheduled* days in the window (~13-22), not 30, so a perfect user can never reach 100%. (3) Upper bound: `recent_logs` comes from `get_logs(habit_id, thirty_days_ago, today)` where `thirty_days_ago = today - 30`, an INCLUSIVE 31-day span (today minus 30 days through today). If the user logged on all 31 of those dates, `31/30*100 = 103.3%`, a completion rate over 100%. The denominator must be the count of due occurrences in the window, and the window endpoints must be consistent.

**Evidence:**

~~~
habit_service.py:176-178:
    thirty_days_ago = today - timedelta(days=30)
    recent_logs = await get_logs(db, habit_id, thirty_days_ago, today)
    rate = (len(recent_logs) / 30) * 100 if total > 0 else 0.0
get_logs (lines 134-146) uses inclusive bounds `completed_date >= start_date` AND `<= end_date`, so [today-30, today] spans 31 dates. Denominator is the literal 30 regardless of rrule or how long the habit has existed.
~~~

**Fix:**

~~~
Compute the denominator from scheduled occurrences within a precise window, clamped to the habit's creation date:

window_start = max(today - timedelta(days=29), habit.created_at.date())  # 30-day inclusive window
scheduled = [d for d in rrule_dates(habit, window_start, today)]
due = len(scheduled) or 1
completed_in_window = sum(1 for log in recent_logs if log.completed_date in set(scheduled))
rate = min(completed_in_window / due * 100, 100.0)

For a pure daily habit this reduces to completed/elapsed_days, never exceeds 100%, and is fair to brand-new habits.
~~~

---

## [HIGH] Alembic migrations ignore DATABASE_URL env var and always connect to a hardcoded localhost DB

- **File:** `backend/alembic.ini:3`
- **Category:** config/data-layer · **Dimension:** backend-config-secrets · **Verifier confidence:** high

alembic.ini pins `sqlalchemy.url` to a hardcoded `postgresql+asyncpg://postgres:changeme_secure_password@localhost:5432/habits_db`. alembic/env.py builds its engine from that ini section (`configuration = config.get_section(config.config_ini_section, {})`, env.py:40) and never reads `os.environ['DATABASE_URL']`, never calls `config.set_main_option(...)`, and never imports `app.core.config.settings` — I grep-confirmed zero references to os.environ / set_main_option / DATABASE_URL / settings anywhere under alembic/. The backend Dockerfile runs migrations on container start: `CMD ["sh", "-c", "alembic upgrade head && uvicorn ..."]` (Dockerfile:26). Inside the container there is no Postgres on `localhost:5432` (Postgres is the separate `postgres` service per docker-compose.dev.yml:36), so `alembic upgrade head` will fail to connect (or, worse, in a shared-host prod deploy silently target the WRONG database than the app, which uses `settings.DATABASE_URL` from env in database.py:7). The migration step and the app thus disagree about which database they use, and the committed credential is stale/public.

**Evidence:**

~~~
alembic.ini:3  sqlalchemy.url = postgresql+asyncpg://postgres:changeme_secure_password@localhost:5432/habits_db
Dockerfile:26  CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
env.py:40      configuration = config.get_section(config.config_ini_section, {})   # url comes only from the ini, never from env
~~~

**Fix:**

~~~
Drive the migration URL from the same env var the app uses. In alembic/env.py, override the ini before building the engine:

```python
import os
from app.core.config import settings

config = context.config
url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
config.set_main_option("sqlalchemy.url", url)
```
(and leave `sqlalchemy.url =` empty or a clearly-non-secret placeholder in alembic.ini). Now `alembic upgrade head` in the container uses the compose-injected `postgres:5432` URL and stays consistent with the running app. Remove the committed real-looking password from alembic.ini entirely.
~~~

---

## [HIGH] Logout does not revoke the refresh token; the claimed Redis whitelist/revocation does not exist

- **File:** `backend/app/routers/auth.py:78`
- **Category:** security · **Dimension:** frontend-auth-token · **Verifier confidence:** high

CLAUDE.md states: 'Whitelist approach: tokens tracked in Redis for immediate revocation.' This is false in the implementation. A full grep of backend/app for redis/whitelist/revoke/blacklist/jti finds only the REDIS_URL config string — there is zero Redis code, no jti, no token store. decode_token (security.py:35) validates signature + expiry only. Logout merely calls response.delete_cookie, which asks the BROWSER to drop its cookie; it does not invalidate the JWT server-side. Therefore: (a) any refresh token already captured (via the CSRF above, a proxy log, an XSS-readable response, or browser history of a non-Secure cookie) remains valid for the full 7 days regardless of logout; (b) there is no way to revoke a session after compromise; (c) on shared machines, a token copied before logout still works. The access token is also stateless and unrevocable for its 15-minute window. The system advertises immediate revocation but provides none.

**Evidence:**

~~~
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token", path="/")   # auth.py:78 — client-side only
    return {"message": "Logged out"}

# grep redis|whitelist|revoke|blacklist|jti backend/app -> only config.py:10 REDIS_URL. No store. No check in decode_token.
~~~

**Fix:**

~~~
Implement the documented whitelist. On login/register add a `jti` (uuid) to the refresh JWT and store it in Redis (key f'rt:{user_id}:{jti}' with TTL = refresh lifetime). In get_refresh_token_payload, after decoding, assert the jti exists in Redis else 401. On /logout, read+decode the cookie, delete its jti from Redis (server-side revocation), then delete the cookie. Add a 'logout all' that deletes rt:{user_id}:* . For access-token revocation within its 15-min window, check a per-user 'tokens-valid-after' timestamp in get_current_user.
~~~

---

## [HIGH] Hardcoded fallback JWT_SECRET ships a known signing key if the env var is unset

- **File:** `backend/app/core/config.py:6`
- **Category:** security · **Dimension:** frontend-auth-token · **Verifier confidence:** high

JWT_SECRET defaults to the literal 'dev-secret-key-change-in-production-min-32-chars'. Settings loads env_file '../.env.local' (config.py:14); in any deployment where that file is missing, mis-pathed, or the var is simply not exported, the app silently starts with this public, source-controlled secret. Because both access and refresh tokens are HS256-signed with this key (security.py:17-32), anyone who knows the default (it is in the repo) can forge a refresh or access token for ANY user id and fully authenticate — get_current_user (deps.py:22) trusts any token that decodes with this secret and has type=='access'. There is no startup assertion that the secret was overridden. This converts a config oversight into full account takeover.

**Evidence:**

~~~
class Settings(BaseSettings):
    ...
    JWT_SECRET: str = "dev-secret-key-change-in-production-min-32-chars"   # config.py:6 — known, in repo
    JWT_ALGORITHM: str = "HS256"
    model_config = {"env_file": "../.env.local", "extra": "ignore"}        # if file absent -> default used silently
~~~

**Fix:**

~~~
Make the secret mandatory with no usable default and fail fast:

from pydantic import field_validator
class Settings(BaseSettings):
    JWT_SECRET: str  # no default -> Pydantic raises if missing
    @field_validator('JWT_SECRET')
    @classmethod
    def _strong(cls, v: str) -> str:
        if len(v) < 32 or v.startswith('dev-secret'):
            raise ValueError('JWT_SECRET must be a strong, non-default value >= 32 chars')
        return v

This prevents the process from booting with the committed key.
~~~

---

## [HIGH] Toggling completion on the detail page invalidates the wrong query keys, leaving the entire page stale

- **File:** `frontend/src/hooks/useHabits.ts:57`
- **Category:** cache-invalidation · **Dimension:** frontend-data-fetching · **Verifier confidence:** high

useToggleHabit's onSuccess only invalidates the list query key ["habits"]. But the habit detail page (frontend/src/app/(dashboard)/habits/[id]/page.tsx) renders entirely from three OTHER query keys: useHabit(id) -> ["habit", id], useAnalytics(id) -> ["analytics", id], and useCalendar(id) -> ["calendar", id]. None of those are invalidated by the toggle. So when a user taps the Today button on the detail page, the POST/DELETE succeeds on the server but the on-screen 'Completed/Not yet' label, the current/longest streak tiles, the completion-rate/total tiles, and the year heatmap all keep showing the pre-toggle values until something else forces a refetch (navigation away and back, or the 30s staleTime expiring AND a refetch trigger). The optimistic-looking green button flips because it is driven by habit.completed_today from the ["habit", id] cache — except that cache is never updated either, so even the button label is stale. Net effect: the primary action of the detail screen appears to do nothing.

**Evidence:**

~~~
// useHabits.ts:34-61 — toggle only touches ["habits"]
export function useToggleHabit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ habitId, date, completed }) => { ... },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["habits"] });
    },
  });
}

// habits/[id]/page.tsx:70-73 — detail reads from habit/analytics/calendar keys
const { data: habit, isLoading } = useHabit(id);        // ["habit", id]
const { data: analytics } = useAnalytics(id);           // ["analytics", id]
const toggle = useToggleHabit();
// ...HeatmapGrid uses useCalendar(habit.id)            // ["calendar", id]
~~~

**Fix:**

~~~
Invalidate every key the toggle affects. Either broaden onSuccess in useToggleHabit, or accept the habitId in onSuccess to scope it:

onSuccess: (_data, { habitId }) => {
  qc.invalidateQueries({ queryKey: ["habits"] });
  qc.invalidateQueries({ queryKey: ["habit", habitId] });
  qc.invalidateQueries({ queryKey: ["analytics", habitId] });
  qc.invalidateQueries({ queryKey: ["calendar", habitId] });
}

(The mutation variables are available as the 2nd arg of onSuccess in TanStack Query v5.)
~~~

---

## [HIGH] No optimistic update + stale 'completed' flag makes double-tap toggles fire conflicting requests (409/404) that fail silently

- **File:** `frontend/src/hooks/useHabits.ts:34`
- **Category:** race-condition · **Dimension:** frontend-data-fetching · **Verifier confidence:** high

useToggleHabit performs no optimistic update and no onError handling, and the request it sends is chosen by branching on the `completed` boolean passed from the caller, which is read from possibly-stale cache (habit.completed_today). On the list page each HabitCard owns its own useToggleHabit instance, and the button is only disabled while THAT instance isPending. But because the cache is not updated until the mutation settles AND the ["habits"] refetch returns, a fast second interaction (or an interaction on the detail page button, which is a different mutation instance from the card) reads the same stale completed=false and POSTs again. The backend then raises ValueError('Already logged for this date') -> HTTP 409 (routers/habits.py:133-136). The inverse races to two DELETEs -> the second returns 404 ('Log not found', habits.py:153-154). Either way there is NO onError on the mutation and no UI surface for mutation failure, so the user sees the toggle silently revert or do nothing while the server rejects the call. The disabled={toggle.isPending} guard does not help across two different mutation instances (card vs detail) or across the optimistic gap.

**Evidence:**

~~~
// useHabits.ts:46-55 — branch on caller-supplied (stale) `completed`
if (completed) {
  await apiJson(`/api/v1/habits/${habitId}/log/${date}`, { method: "DELETE" });
} else {
  await apiJson(`/api/v1/habits/${habitId}/log`, { method: "POST", body: JSON.stringify({ completed_date: date }) });
}
// no onMutate, no onError, no rollback

// backend rejects the duplicate/missing op:
// habits.py:135-136 -> raise HTTPException(status_code=409, detail=str(e))
// habits.py:153-154 -> raise HTTPException(status_code=404, detail="Log not found")
~~~

**Fix:**

~~~
Add an optimistic update with rollback so the UI flips instantly and the branch reads fresh state, and treat the idempotency-violation responses as success. Pattern:

return useMutation({
  mutationFn: async ({ habitId, date, completed }) => { /* as before */ },
  onMutate: async ({ habitId, completed }) => {
    await qc.cancelQueries({ queryKey: ["habits"] });
    const prev = qc.getQueryData<Habit[]>(["habits"]);
    qc.setQueryData<Habit[]>(["habits"], (old) =>
      old?.map((h) => h.id === habitId ? { ...h, completed_today: !completed } : h));
    qc.setQueryData<Habit>(["habit", habitId], (h) => h ? { ...h, completed_today: !completed } : h);
    return { prev };
  },
  onError: (_e, _vars, ctx) => { if (ctx?.prev) qc.setQueryData(["habits"], ctx.prev); },
  onSettled: (_d, _e, { habitId }) => { qc.invalidateQueries({ queryKey: ["habits"] }); qc.invalidateQueries({ queryKey: ["habit", habitId] }); },
});

Also make the backend idempotent: POST on an existing log should 200/204 instead of 409, and DELETE of a missing log should 204 instead of 404, so concurrent toggles converge.
~~~

---

## [HIGH] Toggling completion on the detail page silently does nothing (mutation invalidates only ["habits"], not the habit/analytics/calendar caches)

- **File:** `frontend/src/hooks/useHabits.ts:57-60`
- **Category:** react-correctness · **Dimension:** frontend-react-a11y · **Verifier confidence:** high

useToggleHabit's onSuccess invalidates ONLY the ["habits"] list query. But the habit detail page (app/(dashboard)/habits/[id]/page.tsx) reads from completely different query keys: useHabit -> ["habit", id], useAnalytics -> ["analytics", id], and useCalendar -> ["calendar", id]. None of those are invalidated. Consequently, when a user taps the large Today toggle on the detail page (line 149-156), the mutation succeeds on the server but the UI does NOT update: habit.completed_today, current_streak, longest_streak, the stat cards, and the heatmap all keep showing stale data until a full page reload. To the user the toggle button appears broken. There is also no optimistic update, so even on the list page there is a visible round-trip flicker, and an error leaves no rollback path because nothing was optimistically changed.

**Evidence:**

~~~
onSuccess: () => {
  qc.invalidateQueries({ queryKey: ["habits"] });
},  // detail page reads ["habit",id], ["analytics",id], ["calendar",id] — never invalidated
~~~

**Fix:**

~~~
Invalidate every dependent key (and ideally do an optimistic update):

export function useToggleHabit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ habitId, date, completed }) => {
      if (completed) await apiJson(`/api/v1/habits/${habitId}/log/${date}`, { method: "DELETE" });
      else await apiJson(`/api/v1/habits/${habitId}/log`, { method: "POST", body: JSON.stringify({ completed_date: date }) });
    },
    onSuccess: (_d, { habitId }) => {
      qc.invalidateQueries({ queryKey: ["habits"] });
      qc.invalidateQueries({ queryKey: ["habit", habitId] });
      qc.invalidateQueries({ queryKey: ["analytics", habitId] });
      qc.invalidateQueries({ queryKey: ["calendar", habitId] });
    },
  });
}
~~~

---

## [HIGH] "Today" is computed as the UTC date in the browser, so users west/east of UTC log or un-log the wrong day

- **File:** `frontend/src/components/habits/HabitCard.tsx:9`
- **Category:** react-correctness · **Dimension:** frontend-react-a11y · **Verifier confidence:** high

Both HabitCard (line 9) and the detail page (app/(dashboard)/habits/[id]/page.tsx:98) compute `today` with `new Date().toISOString().split("T")[0]`. `Date.prototype.toISOString()` always serialises in UTC, so this is NOT the user's local calendar day — it is the UTC day. For a user in America/Los_Angeles (UTC-7/8), any time after ~4-5pm local the UTC date has already rolled to tomorrow, so the app POSTs `completed_date` for the wrong date and the DELETE path targets the wrong date. Worse, the backend independently derives `completed_today` from server-side `date.today()` (backend/app/routers/habits.py:64 `today = date.today()`), so the value used to render the toggle (server's day) and the value sent by the toggle (browser's UTC day) can disagree, producing a button whose state never matches what the user just did. CLAUDE.md explicitly states 'Daily reset determined by user's midnight, not UTC midnight' — this code violates that contract.

**Evidence:**

~~~
const today = new Date().toISOString().split("T")[0]; // UTC date, not user-local — at 5pm PST this is already tomorrow
~~~

**Fix:**

~~~
Derive the local calendar date without UTC conversion (and align the backend to the user's stored IANA timezone). A correct local-date helper:

export function localToday(tz?: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit",
  }).format(new Date()); // en-CA yields YYYY-MM-DD
}

Pass the user's `timezone` (already on the User type) and use the same source of truth on the server when computing completed_today.
~~~

---

## [HIGH] CreateHabitModal is not an accessible dialog: no role/aria-modal, no focus trap, no Escape/backdrop close, focus leaks to page behind

- **File:** `frontend/src/components/habits/CreateHabitModal.tsx:24-26`
- **Category:** accessibility · **Dimension:** frontend-react-a11y · **Verifier confidence:** high

The modal is a plain stack of <div>s. It has: (1) no role="dialog" and no aria-modal="true", so assistive tech does not announce it as a modal or scope navigation to it; (2) no aria-labelledby pointing at the 'New Habit' <h2>; (3) no focus trap — pressing Tab from the last control (Create) moves focus to the page behind the overlay (the FAB, the logout button, habit links), which is still in the tab order and still operable; (4) no Escape-to-close handler; (5) the backdrop div has an onClick of nothing, so clicking outside does not dismiss (users expect it to). Keyboard and screen-reader users effectively get trapped behind, not within, the dialog. autoFocus on the name input (line 41) is the only correct piece. On close, focus is also not returned to the element that opened the modal.

**Evidence:**

~~~
<div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
  <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md shadow-2xl">
    <h2 className="text-xl font-bold mb-5">New Habit</h2>  // no role, no aria-modal, no aria-labelledby, no Esc, no focus trap
~~~

**Fix:**

~~~
Make it a real dialog. Minimal native approach uses the <dialog> element or, keeping divs, add roles + key handling + backdrop click + focus restore:

useEffect(() => {
  const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
  document.addEventListener("keydown", onKey);
  return () => document.removeEventListener("keydown", onKey);
}, [onClose]);

<div role="presentation" onClick={onClose} className="fixed inset-0 bg-black/60 ...">
  <div role="dialog" aria-modal="true" aria-labelledby="new-habit-title"
       onClick={(e) => e.stopPropagation()} className="...">
    <h2 id="new-habit-title">New Habit</h2>
    ...
  </div>
</div>

Add a focus trap (e.g. focus-trap-react or a manual Tab/Shift+Tab cycler) and restore focus to the opener on unmount. Prefer a headless library (Radix Dialog / Headless UI) which provides all of this.
~~~

---

## [HIGH] Zero automated tests across the entire stack, yet `make test` reports green (pytest finds nothing, frontend `test` is a no-op echo)

- **File:** `frontend/package.json:9`
- **Category:** testing · **Dimension:** cross-tests-observability · **Verifier confidence:** high

There are NO tests anywhere in the repo: backend has no `test_*.py`, no `conftest.py`, and no `factories.py` (the directories `backend/tests/...`, `backend/tests/factories.py` promised in CLAUDE.md do not exist); frontend has no `*.test.ts(x)`, no `vitest.config.ts`, and no `__tests__/` (also promised in CLAUDE.md). Worse, the test commands give a FALSE sense of safety. `make test-web` runs `npm test` which is wired to `"test": "echo \"No tests configured yet\""` — it prints a message and exits 0 (success). `make test-api` runs `uv run pytest -v` against a tree with zero test files: pytest exits with code 5 ("no tests ran"), but in many CI setups and in `make test` (which chains `test-api test-web`) this is easy to misread as passing, and there is no coverage gate to catch it. devDependencies also omit the entire documented test stack (`vitest`, `@testing-library/react`, `msw`), so even `npx vitest` would fail. Net effect: every correctness bug below (streak math, completion-rate math, log-race 500s) ships completely unverified, and any future regression is invisible.

**Evidence:**

~~~
frontend/package.json:9 -> "test": "echo \"No tests configured yet\""
Makefile: test-web: -> cd $(ROOT)/frontend && npm test   (so `make test` is green with 0 tests)
backend/pyproject.toml -> [tool.pytest.ini_options] asyncio_mode = "auto"  (pytest configured) but `find backend -name 'test_*.py' -o -name conftest.py` returns NOTHING
~~~

**Fix:**

~~~
1) Make 'no tests' a hard failure, not a no-op. Frontend: add `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `msw` to devDependencies, create `vitest.config.ts`, and set `"test": "vitest run"`. Backend: add `--strict-markers` and treat exit-5 as failure in CI (e.g. `pytest -q || ([ $? -eq 5 ] && exit 1)`), or simply require coverage: `pytest --cov=app --cov-fail-under=70`. 2) Add the missing harness files (`backend/tests/conftest.py` with an async session + httpx.AsyncClient fixture against a throwaway Postgres/SQLite, `frontend/__tests__/setup.ts` with MSW). 3) Add a `.github/workflows/ci.yml` that runs `make lint` and `make test` on every PR so the green/red signal actually gates merges.
~~~

---

## [HIGH] Streak algorithm ignores the habit's RRULE schedule — non-daily habits (weekdays/MWF) have streaks broken every skipped day; core domain logic is untested

- **File:** `backend/app/services/streak_service.py:35`
- **Category:** correctness · **Dimension:** cross-tests-observability · **Verifier confidence:** high

CLAUDE.md states RRULE scheduling is a first-class feature (`FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR`, `FREQ=WEEKLY;BYDAY=MO,WE,FR`) and that streaks are THE core computed value. But `compute_current_streak` (and `compute_longest_streak`) assume every habit is daily: they require strictly consecutive calendar dates (`expected -= timedelta(days=1)`, and `(dates[i]-dates[i-1]).days == 1`). For a weekdays-only habit, a perfect user who completes Mon–Fri has their streak RESET to ~1 every Monday, because Friday→Monday is a 3-day gap. The RRULE column (`habit.rrule`) is read into the response but never consulted by the streak math. The same bug makes `compute_current_streak` return 0 over any weekend for a weekday habit even though the user is fully on track. Because there are zero tests, this headline feature is unverified and silently wrong for any non-daily schedule. Secondary issue in the same function: it does not bound the start — if a future-dated log exists it is filtered by `completed_date <= today`, which is correct, but there is no handling for the schedule at all.

**Evidence:**

~~~
backend/app/services/streak_service.py:35-40 ->
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)   # <-- assumes DAILY; no RRULE awareness
        else:
            break
backend/app/services/streak_service.py:60 -> if (dates[i] - dates[i - 1]).days == 1:  # longest streak also DAILY-only
CLAUDE.md (RRULE Scheduling) -> 'Weekdays: FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR' is an advertised feature
~~~

**Fix:**

~~~
Compute the expected sequence from the habit's RRULE using `dateutil.rrule` (already a dependency) and count consecutive *scheduled* occurrences that have a log, rather than consecutive calendar days. Sketch:

```python
from dateutil.rrule import rrulestr

async def compute_current_streak(db, habit, today=None):
    today = today or date.today()
    logged = {r[0] for r in (await db.execute(select(HabitLog.completed_date).where(HabitLog.habit_id==habit.id, HabitLog.completed_date<=today))).all()}
    rule = rrulestr(habit.rrule, dtstart=habit.created_at.date())
    streak = 0
    for occ in reversed(list(rule.between(habit.created_at.date(), today, inc=True))):
        d = occ.date()
        if d == today and d not in logged:   # today still open -> skip, don't break
            continue
        if d in logged:
            streak += 1
        else:
            break
    return streak
```
Then add table-driven tests covering DAILY, weekdays-over-a-weekend, and MWF schedules — each currently produces a wrong streak.
~~~

---

## [MEDIUM] JWT verification does not require the exp claim — tokens without expiry are accepted as valid forever

- **File:** `backend/app/core/security.py:35`
- **Category:** backend-auth / broken authentication · **Dimension:** backend-auth · **Verifier confidence:** high

decode_token() calls jose.jwt.decode() with only the signature/algorithm checked and no options enforcing required claims. python-jose does NOT require an exp claim by default — a signed token that omits exp passes verification and is treated as valid indefinitely. I verified this empirically against the installed python-jose: jwt.decode(token_without_exp, secret, algorithms=['HS256']) returns the payload with no error. Because get_current_user (deps.py:23) and get_refresh_token_payload (deps.py:45) only check payload.type, any party able to mint a token (see the hardcoded-secret finding — trivially anyone) can produce a non-expiring access OR refresh token. Even absent the secret problem, this defeats the 15-min access-token lifetime the design depends on: a single leaked/replayed token minus its exp can never be aged out, and there is no Redis whitelist to revoke it.

**Evidence:**

~~~
def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
# Empirically: jwt.decode(jwt.encode({'sub':'u1','type':'access'}, secret, 'HS256'), secret, algorithms=['HS256'])
#   -> {'sub': 'u1', 'type': 'access'}  (NO error, no exp required)
~~~

**Fix:**

~~~
Enforce required claims and expiry verification explicitly, and pin the expected token type at decode time:

payload = jwt.decode(
    token,
    settings.JWT_SECRET,
    algorithms=[settings.JWT_ALGORITHM],
    options={
        "require": ["exp", "sub", "type"],
        "verify_exp": True,
    },
)

Consider passing expected_type into decode_token and rejecting mismatches there, so callers cannot forget the type check.
~~~

---

## [MEDIUM] Direct bcrypt with no 72-byte guard crashes register/login on long passwords (unhandled 500 / DoS)

- **File:** `backend/app/core/security.py:9`
- **Category:** backend-auth / correctness & availability · **Dimension:** backend-auth · **Verifier confidence:** high

hash_password and verify_password call bcrypt.hashpw/checkpw directly. The installed bcrypt is 5.0.0, which RAISES ValueError for inputs longer than 72 bytes instead of silently truncating. I confirmed this empirically: bcrypt.hashpw(b'a'*100, bcrypt.gensalt()) raises 'ValueError: password cannot be longer than 72 bytes'. The schema only enforces min_length=8 (schemas/auth.py:6) with no max, so a user registering (or later logging in) with a >72-byte password triggers an uncaught ValueError. There is no global exception handler registered (verified — main.py has none), so FastAPI returns a 500. This is a trivial unauthenticated availability bug on /register and a correctness bug on /login. Note also that passlib[bcrypt]==1.7.4 is declared as a dependency but is entirely unused (code imports `bcrypt` directly), and passlib 1.7.4 is itself incompatible with bcrypt 5.x — dead, misleading dependency.

**Evidence:**

~~~
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
# bcrypt.__version__ == '5.0.0'
# bcrypt.hashpw(b'a'*100, bcrypt.gensalt()) -> ValueError: password cannot be longer than 72 bytes
~~~

**Fix:**

~~~
Either cap input length in the Pydantic schema AND defensively pre-hash/truncate, or adopt a wrapper that handles it. Minimal robust fix:

import hashlib, base64

def _normalize(password: str) -> bytes:
    # pre-hash so length is bounded and full entropy is preserved
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())

def hash_password(password: str) -> str:
    return bcrypt.hashpw(_normalize(password), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_normalize(plain), hashed.encode("utf-8"))

Also add `password: str = Field(..., min_length=8, max_length=128)` to RegisterRequest, and drop the unused passlib dependency.
~~~

---

## [MEDIUM] User-enumeration timing oracle: bcrypt skipped entirely when the email is unknown

- **File:** `backend/app/services/auth_service.py:22`
- **Category:** backend-auth / information disclosure · **Dimension:** backend-auth · **Verifier confidence:** high

authenticate_user looks up the user, and when no user matches it returns None WITHOUT ever calling verify_password. bcrypt is deliberately slow (~tens of ms); skipping it for non-existent accounts makes 'unknown email' responses measurably faster than 'known email, wrong password' responses. Combined with the total absence of rate limiting, this is a reliable timing side channel to enumerate which emails have accounts, before even touching the 409-vs-201 oracle on /register. The short-circuit `not user or not verify_password(...)` guarantees the hash is never computed on the user-absent branch.

**Evidence:**

~~~
async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user
~~~

**Fix:**

~~~
Always perform a bcrypt comparison against a constant dummy hash when the user is absent, so both paths cost the same:

_DUMMY_HASH = bcrypt.hashpw(b"timing-equalizer", bcrypt.gensalt()).decode()

async def authenticate_user(db, email, password):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    target_hash = user.password_hash if user else _DUMMY_HASH
    ok = verify_password(password, target_hash)
    return user if (user and ok) else None

This equalizes timing; pair it with the rate-limiting fix to close enumeration.
~~~

---

## [MEDIUM] Malformed sub claim and concurrent-duplicate registration surface as unhandled 500s

- **File:** `backend/app/core/deps.py:30`
- **Category:** backend-auth / error handling & race · **Dimension:** backend-auth · **Verifier confidence:** high

Two robustness defects with no global exception handler to catch them (verified: main.py registers none). (1) get_current_user does UUID(user_id) and refresh does UUID(payload['sub']) on attacker-influenced JWT contents; a token whose sub is not a valid UUID raises ValueError ('badly formed hexadecimal UUID string', confirmed empirically), producing a 500 instead of a clean 401. (2) register_user only guards duplicate emails with a pre-check SELECT plus flush(); the actual integrity guarantee is the unique index uq ix_users_email. Two concurrent /register calls for the same email can both pass the SELECT, and the second commit (performed by the get_db wrapper, database.py:15) raises IntegrityError — which, lacking any handler, returns a 500 rather than the intended 409. The pre-check is a TOCTOU that does not prevent the race.

**Evidence:**

~~~
result = await db.execute(select(User).where(User.id == UUID(user_id)))  # deps.py:30, ValueError on bad sub
user = await get_user_by_id(db, UUID(payload["sub"]))  # auth.py:68, same
# register_user: SELECT-then-flush, no IntegrityError handling:
existing = await db.execute(select(User).where(User.email == email))
if existing.scalar_one_or_none():
    raise ValueError("Email already registered")
user = User(email=email, password_hash=hash_password(password), timezone=tz)
db.add(user); await db.flush()
~~~

**Fix:**

~~~
(1) Parse the UUID defensively and raise 401, e.g.:

try:
    uid = UUID(user_id)
except (ValueError, TypeError):
    raise HTTPException(401, "Invalid token")

(2) Rely on the DB constraint as the source of truth and translate the violation: wrap the insert and `except IntegrityError: await db.rollback(); raise ValueError("Email already registered")` so the router's existing ValueError->409 mapping fires. Also register a global handler for IntegrityError/ValueError in main.py so no DB/parse error leaks as a 500.
~~~

---

## [MEDIUM] Documented Redis token-revocation whitelist is entirely unimplemented; logout and refresh provide no server-side session invalidation

- **File:** `backend/app/core/deps.py:15`
- **Category:** authz-idor / session-management · **Dimension:** backend-authz-idor · **Verifier confidence:** high

CLAUDE.md states the auth design is: "Whitelist approach: tokens tracked in Redis for immediate revocation." No such mechanism exists. `get_current_user` (deps.py:15-35) accepts any correctly-signed, unexpired access token with no lookup against Redis or any allow/deny store. `redis` is not even a dependency (grep of pyproject.toml returns nothing) and no module imports it. `logout` (auth.py:76-79) only calls `response.delete_cookie("refresh_token")` — it does not invalidate the refresh token server-side, so the same refresh token continues to work at `POST /api/v1/auth/refresh` (auth.py:63-73) to mint fresh 15-minute access tokens for the full 7-day refresh window. Consequences: (1) a leaked/stolen access token is valid for its entire 15-min lifetime with no kill switch; (2) a leaked refresh token (or one left on a shared machine after "logout") grants persistent account access for 7 days; (3) there is no way to revoke a compromised user's sessions. This is a broken-access-control gap: the system has no enforcement of the revocation it claims to provide.

**Evidence:**

~~~
deps.py:22-35  payload = decode_token(...)  ... user = result.scalar_one_or_none()  # no revocation/whitelist check
auth.py:76-79  @router.post("/logout") ... response.delete_cookie("refresh_token", path="/"); return {"message": "Logged out"}  # client-side only
auth.py:63-73  refresh() mints a new access token from any valid refresh token, no server-side revocation list consulted
(grep) `redis` absent from backend/pyproject.toml and from all app/ imports
~~~

**Fix:**

~~~
Implement the revocation store the design promises. Add a redis client; on login/refresh store a per-token `jti` (add `"jti": uuid4().hex` to the token payload in security.py) in Redis keyed by user with the token TTL. In `get_current_user`, after decoding, reject if the `jti` is absent from the allow-set (whitelist) or present in a deny-set (blacklist). In `logout`, delete the refresh token's `jti` from Redis (and optionally blacklist the presented access token's `jti`). Example guard:

    jti = payload.get("jti")
    if not jti or not await redis.sismember(f"sess:{user_id}", jti):
        raise HTTPException(401, "Token revoked")

Also rotate the refresh token on each `/refresh` (issue new, revoke old) to limit replay.
~~~

---

## [MEDIUM] get_habit ignores archived_at, so soft-deleted habits stay fully readable and writable; DELETE is non-idempotent

- **File:** `backend/app/services/habit_service.py:75`
- **Category:** authz-idor / resource-lifecycle · **Dimension:** backend-authz-idor · **Verifier confidence:** high

`archive_habit` implements DELETE as a soft delete by setting `habit.archived_at` (habit_service.py:90-94), and `list_habits` correctly hides archived rows with `Habit.archived_at.is_(None)` (habit_service.py:24). But the per-resource ownership gate `get_habit` filters only `Habit.id == habit_id AND Habit.user_id == user_id` (habit_service.py:75-79) — it does NOT exclude archived habits. Every single-resource endpoint routes through `get_habit`: GET /{id}, PUT /{id}, DELETE /{id}, POST /{id}/log, DELETE /{id}/log/{date}, GET /{id}/logs, GET /{id}/calendar, GET /{id}/analytics (habits.py:59,90,116,129,148,166,186,204). Therefore a habit the user 'deleted' is still: editable (PUT), loggable (you can inject new completion rows into a deleted habit via POST /log), log-deletable, and fully readable via analytics/calendar/logs. A deleted resource that remains mutable is an authorization-state defect (the object should be inaccessible post-delete). Additionally, DELETE is not idempotent in a meaningful way: re-archiving an already-archived habit returns 204 and silently overwrites `archived_at` rather than 404/no-op, and there is no endpoint to list or restore archived habits, so they become orphaned-but-live data.

**Evidence:**

~~~
habit_service.py:75-79
    async def get_habit(db, habit_id, user_id):
        result = await db.execute(select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id))
        return result.scalar_one_or_none()   # no `Habit.archived_at.is_(None)`
habit_service.py:24 (list)   .where(Habit.user_id == user_id, Habit.archived_at.is_(None))   # archived hidden HERE but nowhere else
habit_service.py:90-94  archive_habit sets archived_at; reachable again through get_habit on every mutating route
~~~

**Fix:**

~~~
Make the ownership gate also enforce the lifecycle. Either add the filter directly:

    select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id, Habit.archived_at.is_(None))

or add an `include_archived: bool = False` parameter so the few legitimate read-archived cases opt in explicitly. In `archive_habit`, treat an already-archived habit as a no-op/404 to make DELETE idempotent, and add an explicit restore/list-archived path if archived habits are meant to be recoverable.
~~~

---

## [MEDIUM] TOCTOU race in log_completion: duplicate-date check-then-insert surfaces an unhandled 500 instead of 409 under concurrency

- **File:** `backend/app/services/habit_service.py:97`
- **Category:** concurrency / correctness · **Dimension:** backend-authz-idor · **Verifier confidence:** high

`log_completion` performs a check-then-act: SELECT for an existing `(habit_id, completed_date)` row, and if none, INSERT (habit_service.py:100-117). The router maps the duplicate case via `except ValueError -> 409` (habits.py:133-136). But two concurrent `POST /habits/{id}/log` requests for the same date both pass the SELECT (each sees no row), then both INSERT; the DB unique constraint `uq_habit_log_date` (models/habit_log.py:12-14) rejects the second flush/commit with a SQLAlchemy `IntegrityError`, which is NOT a `ValueError`. So the router's `except ValueError` does not catch it and the request fails with an unhandled 500 (and, because `get_db` commits at the end of the request, the failure can surface at commit time outside the try block entirely). The Python-level pre-check is also racy by construction, so the friendly 409 path is not reliable. This is a correctness/robustness defect in the core logging flow.

**Evidence:**

~~~
habit_service.py:100-117
    existing = await db.execute(select(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.completed_date == data.completed_date))
    if existing.scalar_one_or_none():
        raise ValueError("Already logged for this date")
    log = HabitLog(...); db.add(log); await db.flush()   # racy: concurrent inserts hit uq_habit_log_date
habits.py:133-136  try: log = await habit_service.log_completion(...)
                   except ValueError as e: raise HTTPException(409, str(e))   # IntegrityError is NOT ValueError
habit_log.py:12-14  UniqueConstraint("habit_id","completed_date", name="uq_habit_log_date")
~~~

**Fix:**

~~~
Rely on the DB constraint as the source of truth and translate its violation. Use an idempotent upsert or catch IntegrityError:

    from sqlalchemy.exc import IntegrityError
    log = HabitLog(habit_id=habit_id, completed_date=data.completed_date, notes=data.notes)
    db.add(log)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Already logged for this date")

or use `pg_insert(HabitLog).on_conflict_do_nothing(constraint="uq_habit_log_date")` and report 409 when zero rows are inserted. Either removes the race and guarantees a 409 instead of a 500.
~~~

---

## [MEDIUM] Non-UUID JWT `sub` claim triggers an unhandled ValueError -> 500 (no try/except, no global handler)

- **File:** `backend/app/core/deps.py:30`
- **Category:** exception-leakage · **Dimension:** backend-injection-validation · **Verifier confidence:** high

`get_current_user` takes the `sub` claim straight out of a decoded token and passes it to the stdlib UUID() constructor without any guarding: `select(User).where(User.id == UUID(user_id))`. If the token's `sub` is not a valid UUID string (e.g. "admin", "1", "' OR 1=1", or any structurally-valid JWT minted with a non-UUID subject), UUID() raises ValueError: badly formed hexadecimal UUID string. This is NOT caught -- the surrounding code only raises HTTPException for the not-credentials / type!=access / missing-sub cases, and UUID() is on the unguarded line 30. The identical bug exists at auth.py:68 in the /refresh route: `await get_user_by_id(db, UUID(payload["sub"]))`. Because there is NO global exception handler registered (app/main.py adds none and the core/exceptions.py promised by CLAUDE.md does not exist), the ValueError propagates to Starlette and returns HTTP 500. With Postgres asyncpg the UUID is type-checked in Python before the query, so this is a crash not SQLi -- but it is a trivially reachable 500 and a comparison-coercion footgun.

**Evidence:**

~~~
deps.py:30  `result = await db.execute(select(User).where(User.id == UUID(user_id)))` -- preceding lines only `raise HTTPException(...)`, no try/except wraps the UUID(user_id) call. auth.py:68  `user = await get_user_by_id(db, UUID(payload["sub"]))` -- same pattern, also unguarded.
~~~

**Fix:**

~~~
Parse defensively and convert failure into 401, not 500:

```python
from uuid import UUID
try:
    uid = UUID(user_id)
except (ValueError, TypeError):
    raise HTTPException(status_code=401, detail="Invalid token")
result = await db.execute(select(User).where(User.id == uid))
```
Apply the same in auth.py /refresh. Better: standardize the sub round-trip with a single helper parse_subject(payload) -> UUID used by both call sites.
~~~

---

## [MEDIUM] No global exception handler -- uncaught errors (ValueError, IntegrityError, DataError) leak as 500s / stack traces

- **File:** `backend/app/main.py:7`
- **Category:** exception-leakage · **Dimension:** backend-injection-validation · **Verifier confidence:** high

CLAUDE.md documents app/core/exceptions.py ('Custom exception handlers') and the convention 'custom exception classes -> global handlers -> consistent JSON responses'. In reality the file does NOT exist (ls app/core/ shows only __init__, config, deps, security) and main.py registers ZERO exception handlers -- no @app.exception_handler, no add_exception_handler, no override of RequestValidationError. The app is built with docs_url="/docs" and no explicit debug setting, so every uncaught exception falls through to Starlette's default ServerErrorMiddleware. Concretely: (a) the UUID(...) ValueErrors above become bare 500s; (b) the race in log_completion (the pre-check at habit_service.py:101-106 passes, then two concurrent identical-date logs collide on the uq_habit_log_date UniqueConstraint at flush, habit_service.py:115) raises IntegrityError that is never translated to the intended 409; (c) over-length name/color (see other findings) raise DataError/StringDataRightTruncation. With tracebacks enabled (the default unless explicitly hardened, trivially mis-set in a dev/staging container) these responses include file paths, the SQL statement, and bound parameters. There is no central place enforcing a generic 500 body.

**Evidence:**

~~~
main.py (entire file, 28 lines) contains only `app.add_middleware(CORSMiddleware, ...)` and route includes -- no `app.add_exception_handler(...)`, no `@app.exception_handler`. `ls app/core/` -> `config.py deps.py security.py __init__.py` (no exceptions.py, contradicting CLAUDE.md's documented structure).
~~~

**Fix:**

~~~
Add app/core/exceptions.py with handlers and register them in main.py:

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

@app.exception_handler(IntegrityError)
async def _integrity(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "Conflict"})

@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    logger.exception("unhandled", exc_info=exc)   # log server-side only
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```
Also wrap log_completion's insert in try/except IntegrityError -> ValueError('Already logged for this date') so the router's existing 409 mapping holds under concurrency. Pin debug=False and never expose tracebacks to clients.
~~~

---

## [MEDIUM] HabitUpdate bypasses all create-time validation: unbounded name, unchecked color, free-form rrule

- **File:** `backend/app/schemas/habit.py:14`
- **Category:** schema-gap · **Dimension:** backend-injection-validation · **Verifier confidence:** high

HabitUpdate is four bare optional fields with NO constraints, while HabitCreate at least caps name length and pins a color regex. So an attacker can do via PUT what POST forbids. update_habit (habit_service.py:82-87) blindly setattrs every provided field: `for field, value in data.model_dump(exclude_unset=True).items(): setattr(habit, field, value)`. Impact: (1) name has no max_length -- a name > 255 chars passes Pydantic, then fails at the DB String(255) column on flush, raising an unhandled DataError/StringDataRightTruncation -> 500 (compounded by the missing global handler); (2) color drops the pattern r"^#[0-9a-fA-F]{6}$" entirely -- arbitrary text is accepted (e.g. color="javascript:alert(1)" or a 7+ char string that truncates/errs on String(7)), and that value is rendered straight into the frontend as a color/style, a stored-XSS-adjacent sink; (3) rrule is unvalidated (see RRULE finding). The create-path color regex validates format but the DB column has no CHECK and the regex is not reused on update, so the field is effectively unprotected through the most-used mutation endpoint.

**Evidence:**

~~~
schemas/habit.py:14-18 ->
class HabitUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    rrule: str | None = None
(compare HabitCreate:8 `name: str = Field(..., min_length=1, max_length=255)` and :10 `color: str = Field(default="#3B82F6", pattern=r"^#[0-9a-fA-F]{6}$")`). Applied blindly at habit_service.py:83 `setattr(habit, field, value)`.
~~~

**Fix:**

~~~
Mirror the create constraints on update so partial edits cannot bypass them:

```python
class HabitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    rrule: str | None = None   # + the rrulestr() validator from the RRULE finding
```
Define the field set once (shared mixin / Annotated types) so create and update cannot drift. Optionally add a Postgres CHECK on color (`~ '^#[0-9A-Fa-f]{6}$'`) as defense in depth.
~~~

---

## [MEDIUM] log_completion has a check-then-insert race that surfaces a raw asyncpg UniqueViolation (500) instead of the intended 409, and poisons the session/transaction

- **File:** `backend/app/services/habit_service.py:97-117`
- **Category:** correctness/concurrency · **Dimension:** backend-data-layer · **Verifier confidence:** high

log_completion does SELECT-then-INSERT: it queries for an existing log (lines 101-106) and raises ValueError('Already logged for this date') if found, which the router maps to a 409. But two concurrent POST /log requests for the same (habit_id, completed_date) can both pass the SELECT (each sees no row), then both attempt INSERT. The uq_habit_log_date unique constraint correctly prevents the duplicate row, but the second INSERT raises asyncpg.UniqueViolationError / sqlalchemy IntegrityError on flush() (line 115) — NOT a ValueError. The router only catches ValueError (habits.py:135), so the IntegrityError escapes as an unhandled 500 (there is no global exception handler in main.py). Worse: once a flush raises inside an async session, the session is left in a failed/aborted-transaction state; get_db's `except Exception` will rollback (database.py:16-17), so this particular request recovers, but the user gets a 500 for what should be a benign idempotent 409. The same SELECT-then-write TOCTOU exists in register_user (auth_service.py:11-15) against the unique email constraint, with the same 500-instead-of-409 outcome.

**Evidence:**

~~~
existing = await db.execute(
    select(HabitLog).where(
        HabitLog.habit_id == habit_id, HabitLog.completed_date == data.completed_date
    )
)
if existing.scalar_one_or_none():
    raise ValueError("Already logged for this date")
log = HabitLog(...)
db.add(log)
await db.flush()  # concurrent caller raises IntegrityError here, not ValueError
~~~

**Fix:**

~~~
Make it insert-and-catch (rely on the DB constraint as the source of truth) instead of check-then-insert. Use an upsert or catch IntegrityError: `from sqlalchemy.exc import IntegrityError; ... db.add(log); try: await db.flush(); except IntegrityError: await db.rollback(); raise ValueError('Already logged for this date')`. Even cleaner for idempotency: `from sqlalchemy.dialects.postgresql import insert; stmt = insert(HabitLog).values(...).on_conflict_do_nothing(index_elements=['habit_id','completed_date'])`. Apply the same IntegrityError handling in register_user. Then the router's existing ValueError->409 mapping works for the race.
~~~

---

## [MEDIUM] Per-request commit fires AFTER the response model is built, so a commit/IntegrityError failure returns a 200/201 with a body for data that was never persisted

- **File:** `backend/app/database.py:11-18`
- **Category:** correctness/transaction-boundaries · **Dimension:** backend-data-layer · **Verifier confidence:** high

get_db yields the session, lets the endpoint run, and only commits AFTER the endpoint returns (yield then `await session.commit()`). Services use db.flush() (create_habit:70, log_completion:115, update_habit:85, archive_habit:94, register_user:17) — flush sends SQL but does NOT commit. The endpoint then constructs and returns the Pydantic response from the flushed (not committed) ORM object, and FastAPI serializes it. The actual COMMIT happens later in the dependency teardown. If that commit fails — deferred constraint, serialization failure, connection drop, statement-timeout, or the IntegrityError race from log_completion — the client has ALREADY been told 201 Created with the new resource's id/body, but the row is rolled back and does not exist. This is a classic 'lie to the client' transaction-boundary bug: durability is reported before it is achieved. For POST /habits and POST /log this means the frontend caches a habit/log id that the DB will 404 on. Because there is no global exception handler, a commit failure during teardown also produces an opaque 500 in a context where the success response may already be in flight.

**Evidence:**

~~~
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()   # commit happens AFTER endpoint built the 201 response
        except Exception:
            await session.rollback()
            raise
~~~

**Fix:**

~~~
Commit at the end of the unit of work inside the endpoint/service BEFORE building the response, so failures convert to an error status before any success body is produced — e.g. have write endpoints call `await db.commit()` (then `await db.refresh(obj)`) explicitly, and keep get_db's trailing commit only as a safety net, or remove the implicit commit entirely and make each write service own its commit. At minimum, register a global handler for IntegrityError/SQLAlchemyError in main.py so a teardown failure maps to a deterministic 409/500 instead of an unhandled exception.
~~~

---

## [MEDIUM] completion_rate is computed incorrectly — divides 30-day completions by a fixed 30 (not the habit's scheduled days) and gates on lifetime total, producing wrong percentages

- **File:** `backend/app/services/habit_service.py:175-178`
- **Category:** correctness/business-logic · **Dimension:** backend-data-layer · **Verifier confidence:** high

completion_rate = (len(recent_logs) / 30) * 100. Two defects: (1) The denominator is hardcoded 30, but recent_logs comes from get_logs(thirty_days_ago, today) where thirty_days_ago = today - 30 days — an INCLUSIVE 31-day window (the while/<= range in get_calendar and the >=/<= filter in get_logs both include both endpoints). So a habit completed every single day yields 31/30 = 103.3%, an impossible completion rate that violates the float field's implicit 0-100 semantics. (2) The rate is gated on lifetime `total > 0` rather than recent activity, and the RRULE schedule is ignored entirely: a weekdays-only habit (FREQ=DAILY;BYDAY=MO..FR, per CLAUDE.md) that is perfectly completed scores ~22/30 = 73%, misreporting a 100%-adherent user as 73%. The denominator must be the number of SCHEDULED occurrences in the window, derived from the habit's rrule, not a flat 30.

**Evidence:**

~~~
thirty_days_ago = today - timedelta(days=30)
recent_logs = await get_logs(db, habit_id, thirty_days_ago, today)
rate = (len(recent_logs) / 30) * 100 if total > 0 else 0.0
~~~

**Fix:**

~~~
Compute the denominator from the habit's RRULE over the window using dateutil.rrule: `from dateutil.rrule import rrulestr; scheduled = len(list(rrulestr(habit.rrule, dtstart=window_start).between(window_start, today, inc=True)))` and `rate = (len([d for d in completed if d in scheduled_set]) / scheduled) * 100 if scheduled else 0.0`, clamped to [0,100]. Also fix the window: use `today - timedelta(days=29)` for a true 30-day inclusive window (or divide by 31). Pass the Habit object into get_analytics (currently only habit_id is passed at habits.py:208) so the rrule is available.
~~~

---

## [MEDIUM] No connection-pool sizing, pool_pre_ping, or pool_recycle on the async engine — stale/exhausted connections under load and after DB restarts

- **File:** `backend/app/database.py:7`
- **Category:** data-layer/reliability · **Dimension:** backend-data-layer · **Verifier confidence:** high

create_async_engine is called with only the URL and echo=False — no pool_size, max_overflow, pool_pre_ping, or pool_recycle. The default async QueuePool is small (pool_size=5, max_overflow=10), and with the N+1 patterns above each dashboard request holds its single pooled connection for the duration of dozens of sequential awaited round-trips, so a handful of concurrent dashboard loads can exhaust the pool and block. Without pool_pre_ping=True, connections invalidated by a Postgres restart, a Traefik/idle timeout, or a server-side `idle_in_transaction_session_timeout` are handed to requests and fail with 'connection was closed'/InterfaceError on first use. Without pool_recycle, long-lived connections can exceed Postgres/proxy idle limits. For a containerized deployment behind Traefik (per CLAUDE.md) this reliably produces intermittent 500s after the DB or proxy recycles connections.

**Evidence:**

~~~
engine = create_async_engine(settings.DATABASE_URL, echo=False)
~~~

**Fix:**

~~~
Configure the engine explicitly: `create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=1800, pool_size=10, max_overflow=20)`. pool_pre_ping validates connections before use (eliminating post-restart failures), pool_recycle caps connection age below Postgres/proxy idle timeouts, and the larger pool absorbs concurrent requests. Combined with fixing the N+1 patterns so connections are released faster.
~~~

---

## [MEDIUM] compute_current_streak counts future-dated logs as part of the current streak

- **File:** `backend/app/services/streak_service.py:16`
- **Category:** correctness · **Dimension:** backend-streak-correctness · **Verifier confidence:** high

`log_completion` performs ZERO validation on `completed_date` (HabitLogCreate only types it as `date`), so a client can POST a log dated in the future. `compute_current_streak` filters with `HabitLog.completed_date <= today`, which is meant to exclude the future — but the bug is subtler and works the other way too: the anchor logic only accepts `dates[0] == today` or `dates[0] == today - 1`. If a future log exists, the `<= today` filter drops it so the anchor still anchors on today/yesterday — however `compute_longest_streak` (which does NOT filter by today at all, line 47-49) happily includes future dates and will count a fabricated future run as the user's 'longest streak'. Combined with no future-date guard, a user (or a buggy client that computed the wrong UTC date) can inflate 'longest_streak' arbitrarily and pollute analytics (best_day, weekly_counts, total_completions all ingest future logs). The unique constraint does not help because each future date is distinct.

**Evidence:**

~~~
habit_service.py log_completion (lines 97-117) never checks `data.completed_date` against today — it only checks for a duplicate date, then inserts. schemas/habit.py:36-37 `class HabitLogCreate: completed_date: date` (no bound). streak_service.py compute_longest_streak lines 46-49 selects ALL dates with no `<= today` filter:
    select(HabitLog.completed_date).where(HabitLog.habit_id == habit_id).order_by(HabitLog.completed_date)
so a row dated 2030-01-01 is counted in the longest-streak scan and in get_analytics' all_dates.
~~~

**Fix:**

~~~
Reject future completions at the boundary, in the user's timezone. In log_completion (or via a Pydantic validator with access to user tz):

if data.completed_date > user_today(user):
    raise ValueError('Cannot log a completion for a future date')

And defensively bound the analytics/longest-streak queries with `HabitLog.completed_date <= today` so even pre-existing bad rows can't inflate stats. Add a CHECK or application guard; cover with a test that POSTs a future date and expects 422/400.
~~~

---

## [MEDIUM] Streak/analytics recomputed per-habit with N+1 queries on every list call — unbounded full-history scans

- **File:** `backend/app/services/habit_service.py:31`
- **Category:** performance · **Dimension:** backend-streak-correctness · **Verifier confidence:** high

`list_habits` loops over every habit and, per habit, issues: a full-history SELECT for current streak, a second full-history SELECT for longest streak, and a third SELECT for 'completed today' — 3 queries per habit, none bounded by date. `compute_longest_streak` and `compute_current_streak` pull the habit's ENTIRE log history into Python every time the dashboard renders (CLAUDE.md says streaks are computed, not stored, and to 'Cache in Redis if performance becomes an issue' — but no cache exists). For a user with 30 habits and a few years of logs this is 90+ queries and tens of thousands of rows marshalled on every page load and after every toggle (the mutation invalidates and refetches the whole list). The longest-streak scan in particular grows without bound and will dominate latency as data accumulates.

**Evidence:**

~~~
habit_service.py:31-41 — per-habit loop calling compute_current_streak (full select), compute_longest_streak (full select, no date bound, lines 46-51 of streak_service.py), plus a third query for completed_today. No Redis usage anywhere despite the architectural note. compute_longest_streak selects every row: `select(HabitLog.completed_date).where(HabitLog.habit_id == habit_id)`.
~~~

**Fix:**

~~~
Batch-load logs for all habits in one query (`WHERE habit_id IN (...)` grouped in Python), or compute streaks in SQL with a window-function/gaps-and-islands query. Cache `longest_streak` (it only changes when a new log lands) in Redis keyed by habit_id and invalidate on log create/delete. Bound current-streak work by selecting only the recent tail (e.g. last N scheduled occurrences) rather than full history. This removes the N+1 and the unbounded scan.
~~~

---

## [MEDIUM] No environment-aware validation: app cannot distinguish dev from prod and never enforces secure settings

- **File:** `backend/app/core/config.py:4-17`
- **Category:** config/hardening · **Dimension:** backend-config-secrets · **Verifier confidence:** high

Settings has no ENVIRONMENT/DEBUG concept at all. Nothing in the codebase can answer 'are we in production?', so every environment-sensitive decision is hardcoded to the insecure choice and there is no central place to assert prod invariants. Concretely this is the root cause that makes several other issues unfixable cleanly: the refresh cookie's `secure=False` (auth.py:31,55) is a literal with a comment 'True in production' but no flag exists to flip it; CORS is pinned to localhost (main.py:16); `/docs` and `/redoc` are always exposed (main.py:10-11). PLAN.md lines 545-546 and 604-605 show the intended prod compose injects `JWT_SECRET=${JWT_SECRET}` and a DB password via env, but config.py provides defaults that mask a missing/empty env var, so a deploy that forgets to export `JWT_SECRET` does not fail — it runs on the committed dev key. There is zero startup assertion of any kind.

**Evidence:**

~~~
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:changeme_secure_password@localhost:5432/habits_db"
    JWT_SECRET: str = "dev-secret-key-change-in-production-min-32-chars"
    ...
    model_config = {"env_file": "../.env.local", "extra": "ignore"}

settings = Settings()   # <- no validation, no environment awareness
~~~

**Fix:**

~~~
Add an explicit `ENVIRONMENT` field and a model-level validator that hard-fails when production is configured with insecure values:

```python
from pydantic import model_validator

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"   # development | staging | production
    DEBUG: bool = False
    ...
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @model_validator(mode="after")
    def _enforce_prod(self) -> "Settings":
        if self.is_production:
            if self.JWT_SECRET in _INSECURE or len(self.JWT_SECRET) < 32:
                raise ValueError("Refusing to start: weak JWT_SECRET in production")
            if "changeme" in self.DATABASE_URL or "localhost" in self.DATABASE_URL:
                raise ValueError("Refusing to start: dev DATABASE_URL in production")
        return self
```
Then gate cookie `secure=self.is_production`, docs URLs, and CORS off this property. This makes misconfiguration a loud crash, not a silent downgrade.
~~~

---

## [MEDIUM] Swagger/OpenAPI docs exposed unconditionally and JWT does not require an exp claim — known-secret tokens never expire

- **File:** `backend/app/main.py:10-11`
- **Category:** security/hardening · **Dimension:** backend-config-secrets · **Verifier confidence:** high

Two hardening gaps that compound finding #1. (a) main.py hardcodes `docs_url="/docs"` and `redoc_url="/redoc"`, so the interactive API explorer and full schema are served in every environment including production, with no gate on settings. (b) decode_token (security.py:37) calls `jwt.decode` without passing `options`, so python-jose uses its defaults where `require_exp=False` (confirmed in the installed jose/jwt.py: defaults include 'require_exp': False). While create_access_token/create_refresh_token currently include `exp`, the verifier does not *require* it — a token forged with the public dev secret (finding #1) that simply omits `exp` passes signature + claim validation and is accepted forever, defeating the 15-minute access-token design entirely. There is also no `iss`/`aud` binding, so any token signed with the secret for any purpose is interchangeable.

**Evidence:**

~~~
main.py:10-11  docs_url="/docs", redoc_url="/redoc"   # always on
security.py:37  payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])   # no options -> require_exp defaults False
jose/jwt.py     defaults = { ... 'require_exp': False, ... }
~~~

**Fix:**

~~~
Gate docs off the environment and force expiry verification:

```python
# main.py
app = FastAPI(
    title="Habit Tracker API", version="0.1.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
```
```python
# security.py
payload = jwt.decode(
    token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM],
    options={"require_exp": True, "verify_exp": True},
)
```
Add an explicit pinned algorithm list (already done) and consider an `iss`/`aud` claim to scope tokens. This only matters because the signing key is currently guessable — fixing finding #1 is still the priority.
~~~

---

## [MEDIUM] Weak/committed secrets and non-Secure auth cookie in docker-compose, with no flag to harden for production

- **File:** `docker-compose.dev.yml:38`
- **Category:** security/secrets · **Dimension:** backend-config-secrets · **Verifier confidence:** high

docker-compose.dev.yml hardcodes `JWT_SECRET: dev-secret-change-in-production-min32chars` and `DATABASE_URL: ...postgres:password@postgres...` directly in a committed file. This particular string is one of the values the app would otherwise have to override, and because config.py provides defaults (finding #1) there is nothing stopping this weak value from also being used in a prod-ish run. Separately, the refresh-token cookie is written with `secure=False` at auth.py:31 and :55 (the only difference being a code comment), so the long-lived (7-day) refresh token can be transmitted over plaintext HTTP and intercepted; there is no `settings.is_production` to flip `secure=True`. SameSite is only 'lax', which still permits the cookie to ride along on top-level cross-site navigations. Because the refresh endpoint mints fresh access tokens from this cookie (auth.py:63-73), capturing it is equivalent to a durable session hijack.

**Evidence:**

~~~
docker-compose.dev.yml:38  JWT_SECRET: dev-secret-change-in-production-min32chars
auth.py:31  secure=False,  # True in production with HTTPS
auth.py:55  secure=False,
~~~

**Fix:**

~~~
1) Never commit real secret values: in compose use `JWT_SECRET: ${JWT_SECRET:?set in .env}` and `DATABASE_URL: ${DATABASE_URL:?}` so docker compose fails if the env var is unset (matches PLAN.md's `${JWT_SECRET}` intent). Keep actual values only in an un-committed `.env` (already in .gitignore). 2) Drive cookie security off config and centralize the cookie creation:
```python
response.set_cookie(
    key="refresh_token", value=refresh_token, httponly=True,
    samesite="strict" if settings.is_production else "lax",
    secure=settings.is_production,
    max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, path="/api/v1/auth",
)
```
Narrowing `path` to the auth prefix also limits cookie exposure. Rotate the dev secret out of git history if it was ever used anywhere real.
~~~

---

## [MEDIUM] Concurrent 401s trigger a refresh stampede — N parallel /refresh calls and token overwrites (no in-flight dedupe)

- **File:** `frontend/src/lib/api.ts:47`
- **Category:** concurrency/correctness · **Dimension:** frontend-auth-token · **Verifier confidence:** high

apiFetch performs the refresh-on-401 inline with no mutex or shared in-flight promise. The dashboard mounts multiple TanStack Query hooks that each call apiJson independently and in parallel (useHabits, useHabit, useHabitCalendar, useHabitAnalytics — see frontend/src/hooks/useHabits.ts:10,17,75,83). When the 15-minute access token expires, every in-flight request gets a 401 at roughly the same time and each one independently calls refreshAccessToken(). This fires N simultaneous POST /api/v1/auth/refresh requests and N sequential writes to the module-level `accessToken`. Because refresh tokens are not rotated server-side this 'works' by luck, but it is a real correctness/race defect: it hammers the backend, and if rotation is ever added (recommended) the racing refreshes will invalidate each other and log the user out. Each racer also captured its own `headers` Headers object, so a later racer's Authorization update never reaches an earlier racer's retry.

**Evidence:**

~~~
// api.ts
let accessToken: string | null = null;          // line 3 — shared mutable, no lock
...
  if (res.status === 401 && accessToken) {        // line 47
    const newToken = await refreshAccessToken();  // line 48 — every caller does this
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: "include" });
    }
  }
~~~

**Fix:**

~~~
Deduplicate refresh with a single shared promise so concurrent 401s await one refresh:

let refreshPromise: Promise<string | null> | null = null;
function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/auth/refresh`, { method: 'POST', credentials: 'include' });
        if (!res.ok) return null;
        const data = await res.json();
        accessToken = data.access_token;
        return accessToken;
      } catch { return null; }
      finally { refreshPromise = null; }
    })();
  }
  return refreshPromise;
}

This collapses N concurrent refreshes into one and is the prerequisite for safe refresh-token rotation.
~~~

---

## [MEDIUM] Refresh cookie is cross-subdomain-broken AND insecure in production: no Domain attribute, Secure=False hardcoded

- **File:** `backend/app/routers/auth.py:31`
- **Category:** security/correctness · **Dimension:** frontend-auth-token · **Verifier confidence:** high

The refresh_token cookie is written by the API host with no `domain=` parameter and secure=False. Two compounding problems: (1) Production runs the API on api.habits.armandointeligencia.com and the SPA on habits.armandointeligencia.com (CLAUDE.md 'Port Assignments' / domains). A cookie set without a Domain attribute is host-only — it scopes to api.habits.* and the browser will NOT send it on requests the SPA makes... except the SPA calls the API host directly via fetch(API_URL) so the cookie does return; however, because the API is HTTPS in prod and the cookie is Secure=False, the cookie is also transmittable over plaintext and is set even on insecure contexts, defeating the whole httpOnly-cookie hardening. (2) secure=False is hardcoded in both register and login with only a comment 'True in production' — there is no environment switch, so a real HTTPS deploy ships insecure cookies. Combined with SameSite=Lax this materially weakens the refresh-token-in-httpOnly-cookie design the architecture relies on.

**Evidence:**

~~~
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,  # True in production with HTTPS   <-- never actually toggled; auth.py:31 and :55
        max_age=7 * 24 * 60 * 60,
        path="/",
    )
# no domain= ; identical insecure block duplicated at login (auth.py:50-58)
~~~

**Fix:**

~~~
Drive cookie flags from settings instead of a literal, and set Secure in prod:

response.set_cookie(
    key='refresh_token', value=refresh_token, httponly=True,
    samesite=settings.COOKIE_SAMESITE,           # 'strict' or 'none'
    secure=settings.COOKIE_SECURE,               # True in prod
    domain=settings.COOKIE_DOMAIN or None,       # e.g. '.habits.armandointeligencia.com' if sharing across subdomains
    max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS*24*3600, path='/',
)

Note: if you ever need the cookie cross-subdomain you must use SameSite=None + Secure=True (None requires Secure). Factor the set_cookie block into one helper to avoid the login/register drift.
~~~

---

## [MEDIUM] 'today' is computed in UTC on the client but as server-local date on the backend, corrupting completions near midnight

- **File:** `frontend/src/components/habits/HabitCard.tsx:9`
- **Category:** correctness-timezone · **Dimension:** frontend-data-fetching · **Verifier confidence:** high

The client derives the completion date as new Date().toISOString().split('T')[0], which is the UTC calendar date — not the user's local date. The backend computes completed_today with Python's date.today() (backend/app/services/habit_service.py:29 and routers/habits.py:63), which is the SERVER process's local date. CLAUDE.md explicitly specifies completions must be keyed to the user's IANA timezone midnight (users.timezone). So three different definitions of 'today' are in play. Concrete failure: a user in America/Los_Angeles toggling a habit at 18:00 PDT sends date='tomorrow' (because UTC is already past midnight), so the POST writes a log for the wrong calendar day; the list's completed_today (server date.today()) then does NOT reflect it, so the UI shows the habit as still incomplete even after a successful write — and the streak math is computed against the wrong day. This also breaks the toggle's read side: habit.completed_today (server day) and the date the button sends (UTC day) can disagree, so the DELETE branch targets a date that has no log -> 404, or the POST branch duplicates -> 409.

**Evidence:**

~~~
// HabitCard.tsx:9
const today = new Date().toISOString().split("T")[0]; // UTC date, NOT user-local

// habits/[id]/page.tsx:98 — same bug
const today = new Date().toISOString().split("T")[0];

// backend habit_service.py:29 — server-local 'today'
today = date.today()
log_result = await db.execute(select(HabitLog).where(HabitLog.habit_id == habit.id, HabitLog.completed_date == today))
~~~

**Fix:**

~~~
Compute the local calendar date on the client (or, better, send the user's timezone and let the server resolve 'today'). Minimal client fix using local components:

function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
const today = localToday();

Long-term: have the backend determine 'today' from user.timezone (zoneinfo) instead of date.today(), so the server day and the client day agree regardless of where the container runs.
~~~

---

## [MEDIUM] CreateHabitModal closes unconditionally after mutateAsync, swallowing errors and giving no feedback on failure

- **File:** `frontend/src/components/habits/CreateHabitModal.tsx:17`
- **Category:** error-handling · **Dimension:** frontend-data-fetching · **Verifier confidence:** high

handleSubmit awaits createHabit.mutateAsync(...) and then calls onClose() with no try/catch. mutateAsync REJECTS on failure (unlike mutate). If the POST /api/v1/habits fails (duplicate name 409, 422 validation, network error, 500), the await throws, the promise from the submit handler rejects unhandled, onClose() is never reached so the modal stays open — but createHabit.error is never read or rendered anywhere, so the user sees the spinner stop and the form just sit there with no message. Worse, because the rejection is an unhandled promise rejection inside an async event handler, the only signal is a console error. There is also no success toast/redirect logic beyond closing. The mutation exposes isError/error but the component ignores them.

**Evidence:**

~~~
// CreateHabitModal.tsx:17-21
async function handleSubmit(e: FormEvent) {
  e.preventDefault();
  await createHabit.mutateAsync({ name, description: description || undefined, color });
  onClose();   // only runs on success; on failure the throw is unhandled and no error UI exists
}
// createHabit.isError / createHabit.error are never rendered in the JSX
~~~

**Fix:**

~~~
Guard the close and render the error:

async function handleSubmit(e: FormEvent) {
  e.preventDefault();
  try {
    await createHabit.mutateAsync({ name: name.trim(), description: description || undefined, color });
    onClose();
  } catch {
    /* error surfaced below via createHabit.error */
  }
}

and in the form JSX:
{createHabit.isError && (
  <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg text-sm">
    {(createHabit.error as Error)?.message || "Could not create habit"}
  </div>
)}
~~~

---

## [MEDIUM] useDeleteHabit swallows all errors with .catch(() => null), so a failed archive still navigates away and refetches as if it succeeded

- **File:** `frontend/src/hooks/useHabits.ts:66`
- **Category:** error-handling · **Dimension:** frontend-data-fetching · **Verifier confidence:** high

The delete mutationFn appends .catch(() => null) to the apiJson call, converting ANY failure (403 on another user's habit, 404, 500, network error) into a resolved mutation. Because the rejection is swallowed, onSuccess ALWAYS fires and invalidates ["habits"], and the caller in habits/[id]/page.tsx:107-111 awaits mutateAsync and then unconditionally router.push('/habits'). So a user whose archive request actually failed is still bounced to the list with a success-path code flow, and the habit reappears after the refetch — a confusing 'it came back' bug with no error shown. Swallowing the error also defeats TanStack Query's retry and error state entirely (isError can never be true).

**Evidence:**

~~~
// useHabits.ts:63-69
export function useDeleteHabit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiJson(`/api/v1/habits/${id}`, { method: "DELETE" }).catch(() => null), // <-- error eaten
    onSuccess: () => qc.invalidateQueries({ queryKey: ["habits"] }),
  });
}

// habits/[id]/page.tsx:107-111 — navigates regardless of real outcome
async function handleDelete() {
  if (!confirm("Archive this habit? You can't undo this.")) return;
  await deleteHabit.mutateAsync(id);
  router.push("/habits");
}
~~~

**Fix:**

~~~
Remove the .catch so failures propagate, then let the caller react:

mutationFn: (id: string) => apiJson(`/api/v1/habits/${id}`, { method: "DELETE" }),
onSuccess: (_d, id) => {
  qc.invalidateQueries({ queryKey: ["habits"] });
  qc.removeQueries({ queryKey: ["habit", id] }); // drop the now-archived detail cache
},

async function handleDelete() {
  if (!confirm(...)) return;
  try { await deleteHabit.mutateAsync(id); router.push("/habits"); }
  catch { /* show deleteHabit.error in the UI */ }
}

Note: DELETE returns 204 No Content (habits.py:110), so apiJson's res.json() will throw on an empty body even on success — handle 204 in apiJson (return undefined when status===204) or this mutation throws on the happy path too.
~~~

---

## [MEDIUM] Detail page shows 'Habit not found' on every transient fetch error, treating errors as 404

- **File:** `frontend/src/app/(dashboard)/habits/[id]/page.tsx:87`
- **Category:** loading-error-state · **Dimension:** frontend-data-fetching · **Verifier confidence:** high

useHabit(id) returns error state, but the detail page ignores the error field entirely. After the isLoading guard passes, it checks `if (!habit)` and renders 'Habit not found'. But habit is also undefined when the query FAILED for any reason (500, network blip, expired auth that the refresh flow couldn't recover, 422). So a temporary backend error is presented to the user as a permanent 'Habit not found' with a 'Back to habits' link — misleading, and it offers no retry. With retry:1 and staleTime:30s, a flaky network produces this false-negative regularly. The list page (habits/page.tsx:67) does distinguish error from empty; the detail page does not.

**Evidence:**

~~~
// habits/[id]/page.tsx:70 — error is destructured-out (not even captured)
const { data: habit, isLoading } = useHabit(id);
// :79 loading guard, then :87:
if (!habit) {
  return (
    <div ...>
      <p className="text-slate-400">Habit not found</p>
      <Link href="/habits" ...>Back to habits</Link>
    </div>
  );
}
// No branch for `error` — a 500/network failure renders the 404 UI.
~~~

**Fix:**

~~~
Capture and branch on error vs. true 404. apiJson throws Error('HTTP 404') for a real not-found; distinguish it:

const { data: habit, isLoading, error } = useHabit(id);
...
if (error && !/404/.test((error as Error).message)) {
  return <RetryState onRetry={() => qc.invalidateQueries({ queryKey: ["habit", id] })} />;
}
if (!habit) { /* genuine not-found UI */ }

Better: have apiJson attach res.status to the thrown error so the check is structural, not string-matching.
~~~

---

## [MEDIUM] Form <label>s are not associated with inputs (no htmlFor/id) and inputs lack autoComplete

- **File:** `frontend/src/app/(auth)/login/page.tsx:49-59`
- **Category:** accessibility · **Dimension:** frontend-react-a11y · **Verifier confidence:** high

Across the login form, register form, and CreateHabitModal, every <label> is a bare element with no htmlFor, and the corresponding <input>/<textarea> has no matching id. Clicking the label text does not focus the field, and screen readers do not announce the label when the field gains focus (the accessible name is missing — they fall back to the placeholder, which is not a substitute). This affects: login email/password (login/page.tsx:49-59,63-75), register email/password/confirm (register/page.tsx:54-65,67-80,82-95), and modal name/description/color (CreateHabitModal.tsx:30-43,46-56,59-61). Additionally none of the auth inputs set autoComplete, so password managers and browser autofill mis-handle them: the password field should be autoComplete="current-password" on login and "new-password" on register, and email "email"/"username".

**Evidence:**

~~~
<label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
<input type="email" value={email} onChange={...} required ... />  // label has no htmlFor, input has no id, no autoComplete
~~~

**Fix:**

~~~
Associate every label and add autoComplete:

<label htmlFor="login-email" className="...">Email</label>
<input id="login-email" type="email" autoComplete="username" value={email} ... />

<label htmlFor="login-password">Password</label>
<input id="login-password" type="password" autoComplete="current-password" ... />

On register use autoComplete="new-password" for both password and confirm. In the modal, give name/description/color-group ids and use htmlFor (the color group should be a fieldset/legend, see separate finding).
~~~

---

## [MEDIUM] Color swatch buttons have no accessible name and the group is not labelled as a radio set

- **File:** `frontend/src/components/habits/CreateHabitModal.tsx:63-75`
- **Category:** accessibility · **Dimension:** frontend-react-a11y · **Verifier confidence:** high

The eight color choices are rendered as <button type="button"> elements whose only content is a background-color style — there is no text, no aria-label, and no title. A screen-reader user hears 'button' eight times with no way to distinguish or know which is selected; the selected state is conveyed purely by a visual ring (lines 68-72) with no aria-pressed/aria-checked. Semantically this is a single-select choice (a radio group) but it is built as eight independent buttons with no grouping label, so the relationship to the 'Color' <label> (line 59) is lost. Keyboard users also cannot arrow between options as they would expect for a radio group.

**Evidence:**

~~~
{COLORS.map((c) => (
  <button key={c} type="button" onClick={() => setColor(c)}
    className={`w-9 h-9 rounded-full ... ${color === c ? "ring-2 ..." : "hover:scale-105"}`}
    style={{ backgroundColor: c }} />  // no aria-label, no aria-pressed, no group role/name
))}
~~~

**Fix:**

~~~
Model it as a labelled radiogroup with named, state-exposing options:

<div role="radiogroup" aria-label="Habit color" className="flex gap-2 flex-wrap">
  {COLORS.map((c) => (
    <button key={c} type="button" role="radio" aria-checked={color === c}
      aria-label={`Color ${c}`} onClick={() => setColor(c)}
      className={...} style={{ backgroundColor: c }} />
  ))}
</div>

Optionally add ArrowLeft/ArrowRight handling to move selection, matching native radio semantics.
~~~

---

## [MEDIUM] Highest-risk untested path: `log_completion` does check-then-insert against a real UNIQUE constraint — concurrent/duplicate taps raise IntegrityError and return HTTP 500 instead of 409

- **File:** `backend/app/services/habit_service.py:97`
- **Category:** concurrency · **Dimension:** cross-tests-observability · **Verifier confidence:** high

This is the single highest-risk untested code path in the backend: the write that every "mark complete" tap hits. `log_completion` SELECTs for an existing row, and if none is found, INSERTs. But `habit_logs` carries `UniqueConstraint("habit_id", "completed_date", name="uq_habit_log_date")` (model + migration). The select-then-insert is not atomic. Two concurrent requests for the same (habit, date) — trivially produced by a double-tap on the toggle, a retry, or two devices — both pass the existence check, then the second INSERT violates the unique constraint. SQLAlchemy raises `IntegrityError` on `flush()`. The router only catches `ValueError` (line 135), so the IntegrityError propagates uncaught: `get_db` rolls back and re-raises, FastAPI returns a generic HTTP 500 with a stack trace, and — because there is zero logging (see separate finding) — nothing structured is recorded. The user-facing 409 ('Already logged for this date') is therefore only delivered on the slow, single-request path; the real-world concurrent path returns a 500. This is exactly the kind of regression a 5-line test would have caught, and there is no test.

**Evidence:**

~~~
backend/app/services/habit_service.py:100-115 ->
    existing = await db.execute(select(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.completed_date == data.completed_date))
    if existing.scalar_one_or_none():
        raise ValueError("Already logged for this date")
    log = HabitLog(...); db.add(log); await db.flush()   # <-- IntegrityError on concurrent dup
backend/app/models/habit_log.py:13 -> UniqueConstraint("habit_id", "completed_date", name="uq_habit_log_date")
backend/app/routers/habits.py:133-136 -> except ValueError as e: raise HTTPException(409, ...)  # IntegrityError NOT caught
~~~

**Fix:**

~~~
Make the insert atomic and map the DB error to 409. Replace check-then-insert with an idempotent upsert or catch the IntegrityError:

```python
from sqlalchemy.exc import IntegrityError

async def log_completion(db, habit_id, data):
    log = HabitLog(habit_id=habit_id, completed_date=data.completed_date, notes=data.notes)
    db.add(log)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Already logged for this date")  # router maps to 409
    await db.refresh(log)
    return log
```
Or use `pg_insert(HabitLog).on_conflict_do_nothing(...)` for true idempotency. Then add the regression test:

```python
async def test_log_completion_duplicate_returns_409(client, habit):
    body = {"completed_date": "2026-06-24"}
    assert (await client.post(f"/api/v1/habits/{habit.id}/log", json=body)).status_code == 201
    r = await client.post(f"/api/v1/habits/{habit.id}/log", json=body)
    assert r.status_code == 409  # currently 500 under concurrency
```
~~~

---

## [MEDIUM] Completion rate divides by a hardcoded 30 regardless of habit age or schedule — brand-new habits show absurdly low rates, and rate can exceed 100%

- **File:** `backend/app/services/habit_service.py:178`
- **Category:** correctness · **Dimension:** cross-tests-observability · **Verifier confidence:** medium

`get_analytics` computes the headline 'completion_rate' as `(len(recent_logs) / 30) * 100`. The denominator is a constant 30 with no relation to (a) how long the habit has existed or (b) how many days the schedule actually called for in the window. Consequences: a habit created 3 days ago and completed all 3 days reports 10% completion (3/30), which is demoralizing and wrong; conversely the numerator `recent_logs` is the count of logs in [today-30, today], and `get_logs` imposes no upper bound at `today`, so any future-dated logs (which the API freely accepts — see related finding) inflate the count and can push the rate ABOVE 100%. The guard `if total > 0 else 0.0` only protects the all-empty case, not the new-habit or future-log cases. This is pure, deterministic logic that is trivial to unit test, yet has no test.

**Evidence:**

~~~
backend/app/services/habit_service.py:175-178 ->
    thirty_days_ago = today - timedelta(days=30)
    recent_logs = await get_logs(db, habit_id, thirty_days_ago, today)
    rate = (len(recent_logs) / 30) * 100 if total > 0 else 0.0   # fixed /30, can exceed 100%
~~~

**Fix:**

~~~
Bound the denominator by the number of *scheduled* days since the habit was created within the window (and clamp the result):

```python
window_start = max(thirty_days_ago, habit.created_at.date())
scheduled_days = count_scheduled_occurrences(habit.rrule, window_start, today)  # via dateutil.rrule
done = sum(1 for l in recent_logs if l.completed_date <= today)
rate = round(min(done / scheduled_days * 100, 100.0), 1) if scheduled_days else 0.0
```
Add unit tests: (new habit, 3/3 days -> 100%), (future log present -> capped at 100%), (no scheduled days -> 0.0).
~~~

---

## [MEDIUM] No backend logging or exception handling anywhere — `core/exceptions.py` promised in CLAUDE.md does not exist; unhandled errors become silent 500s with no audit trail

- **File:** `backend/app/main.py:1`
- **Category:** observability · **Dimension:** cross-tests-observability · **Verifier confidence:** high

The backend has zero observability. `grep -rn 'import logging|logger|getLogger|loguru|structlog' backend/app` returns NOTHING — there is no request logging, no error logging, no access log configuration, and no correlation/request IDs. CLAUDE.md documents `app/core/exceptions.py` ('Custom exception handlers') and an error-handling convention ('custom exception classes -> global handlers -> consistent JSON responses'), but the file does not exist and no `@app.exception_handler` is registered in `main.py`. The practical impact compounds the concurrency finding: when `log_completion` raises IntegrityError, or any other unexpected error occurs, FastAPI returns a generic 500 and NOTHING is logged server-side — there is no way to detect, alert on, or debug production failures. There is also no APM/tracing (`sentry`/`opentelemetry`/`prometheus` all absent). For a service that handles auth and user data, the complete absence of an error/audit log is a real operational defect, not a nicety.

**Evidence:**

~~~
grep for logging in backend/app -> 'NO logging found in backend/app'
backend/app/main.py -> only `app.add_middleware(CORSMiddleware, ...)`; no logging config, no exception handlers, no middleware for request IDs
CLAUDE.md Directory Structure -> 'exceptions.py   # Custom exception handlers'  (file absent: `ls backend/app/core/exceptions.py` -> NO such file)
~~~

**Fix:**

~~~
1) Configure structured logging at startup (`logging.basicConfig`/`structlog`) honoring `settings.LOG_LEVEL` (already in config). 2) Create `app/core/exceptions.py` and register global handlers in `main.py`:

```python
@app.exception_handler(Exception)
async def unhandled(request, exc):
    logger.exception("unhandled error path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```
3) Add a request-ID middleware that logs method/path/status/latency and attaches an `X-Request-ID` so failures are traceable. 4) Wire an APM SDK (Sentry/OTel) given auth+PII are in scope.
~~~

---

## [MEDIUM] Toggle mutation has no error handling and no optimistic rollback — failed completes/undeletes fail silently, leaving the UI desynced from server state

- **File:** `frontend/src/hooks/useHabits.ts:34`
- **Category:** testing · **Dimension:** cross-tests-observability · **Verifier confidence:** high

`useToggleHabit` (the most-used frontend interaction) defines only `onSuccess: invalidateQueries`. There is no `onMutate` (so no optimistic update) and no `onError` (so failures are swallowed). `grep -rn 'onError|onMutate|isError|rollback' frontend/src` returns NOTHING across the whole frontend. In `HabitCard`, `handleToggle` calls `toggle.mutate(...)` and the component never reads `toggle.isError`; on failure the button simply re-enables (`disabled={toggle.isPending}`) with the OLD `habit.completed_today`, giving the user no feedback that the tap failed. Concretely this bites on the exact race from the backend finding: if the POST /log returns 409 (or the DELETE returns 404 because the optimistic mental model is wrong), `apiJson` throws, the mutation rejects, nothing is shown, and the displayed streak/'done today' counts on the page stay stale until a manual refetch. There are no component or hook tests to catch this, and the documented MSW-based test setup does not exist.

**Evidence:**

~~~
frontend/src/hooks/useHabits.ts:34-61 -> useToggleHabit: only `onSuccess: () => qc.invalidateQueries(...)`; no onMutate/onError
frontend/src/components/habits/HabitCard.tsx:11-19 -> handleToggle calls toggle.mutate(...) with no error branch; component never references toggle.isError
grep onError|onMutate|isError|rollback in frontend/src -> 'NO onError/onMutate/isError in frontend src'
~~~

**Fix:**

~~~
Add optimistic update + rollback + visible error to the mutation, then test it with MSW:

```ts
useMutation({
  mutationFn: ...,
  onMutate: async (vars) => {
    await qc.cancelQueries({ queryKey: ["habits"] });
    const prev = qc.getQueryData(["habits"]);
    qc.setQueryData(["habits"], (h) => /* flip completed_today for vars.habitId */);
    return { prev };
  },
  onError: (_e, _vars, ctx) => { qc.setQueryData(["habits"], ctx?.prev); toast.error("Couldn't update habit"); },
  onSettled: () => qc.invalidateQueries({ queryKey: ["habits"] }),
});
```
Test (vitest + MSW): mock POST /log -> 409 and assert the optimistic toggle reverts and an error is surfaced.
~~~

---

## [MEDIUM] API accepts arbitrary future and unbounded-range dates (no `completed_date <= today`, no `start_date <= end_date`) — logs the future, returns empty silently, can build huge calendars

- **File:** `backend/app/routers/habits.py:158`
- **Category:** correctness · **Dimension:** cross-tests-observability · **Verifier confidence:** high

Multiple date inputs are unvalidated, and none of it is tested. (1) `HabitLogCreate.completed_date` is a bare `date` with no upper bound, and neither `log_completion` nor the router checks `completed_date <= user_today`. A client can POST a completion dated years in the future; that row then corrupts `compute_longest_streak`, inflates `total_completions`, and can push `completion_rate` over 100% (see related finding). (2) `get_logs` and `get_calendar` accept `start_date`/`end_date` as free `Query` params and never assert `start_date <= end_date`. An inverted range silently returns an empty list / empty calendar (the `while current <= end_date` loop body never executes) — a confusing no-op rather than a 422. (3) `get_calendar` defaults to a 365-day span but imposes no maximum; a caller passing a far-future `end_date` makes `get_calendar` materialize one `CalendarDay` object per day in a potentially enormous range, an unbounded-work / DoS vector. Pydantic/path validation here is exactly what tests would pin down, and there are none.

**Evidence:**

~~~
backend/app/schemas/habit.py:36-38 -> class HabitLogCreate: completed_date: date  (no upper bound / validator)
backend/app/routers/habits.py:158-175 -> get_logs: start_date/end_date Query(default=None); no `start_date <= end_date` check
backend/app/services/habit_service.py:155-160 -> while current <= end_date: ...  (inverted range -> silent empty; far-future end_date -> unbounded list)
~~~

**Fix:**

~~~
Validate at the boundary. Schema: add a validator rejecting future dates (relative to the user's tz/today):

```python
class HabitLogCreate(BaseModel):
    completed_date: date
    @field_validator("completed_date")
    @classmethod
    def not_future(cls, v):
        if v > date.today():
            raise ValueError("completed_date cannot be in the future")
        return v
```
Routers: after defaulting, `if start_date > end_date: raise HTTPException(422, 'start_date must be <= end_date')` and clamp the span (e.g. `end_date - start_date <= timedelta(days=366)` else 422). Add tests for: future-dated log -> 422; inverted range -> 422; oversized calendar range -> 422.
~~~

---

## [LOW] get_current_user does an unguarded UUID(sub) conversion, turning malformed tokens into 500s instead of 401s

- **File:** `backend/app/core/deps.py:30`
- **Category:** auth-robustness / error-handling · **Dimension:** backend-authz-idor · **Verifier confidence:** high

After decoding the JWT, `get_current_user` extracts `sub` and calls `UUID(user_id)` directly (deps.py:26-31). If a token carries a `sub` that is signature-valid but not a UUID (e.g. a token minted by an older/alternate code path, a test fixture, or any case where `sub` is a non-UUID string), `UUID(user_id)` raises `ValueError`, which is not caught anywhere in the dependency and propagates to a 500 Internal Server Error rather than a clean 401. While exploitability is low (it generally requires the signing key to mint such a token), it is an unhandled exception in the authentication path and a reliability/observability defect: auth failures should be 401s, and a 500 here also leaks that the input reached the DB-lookup stage. The contrast is notable because `auth.refresh` performs the same `UUID(payload["sub"])` (auth.py:68) and is equally fragile.

**Evidence:**

~~~
deps.py:26-31
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))   # UUID() can raise ValueError -> 500
auth.py:68  user = await get_user_by_id(db, UUID(payload["sub"]))   # same unguarded conversion
~~~

**Fix:**

~~~
Validate the claim shape and fail as 401:

    try:
        uid = UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == uid))

Apply the same guard in auth.refresh (auth.py:68). Optionally centralize subject parsing in decode_token so both call sites share one validated path.
~~~

---

## [LOW] RRULE strings are stored and echoed with zero validation (dead python-dateutil dependency)

- **File:** `backend/app/schemas/habit.py:11`
- **Category:** unvalidated-input · **Dimension:** backend-injection-validation · **Verifier confidence:** high

The `rrule` field is the core scheduling primitive of the app (CLAUDE.md: 'Habit frequency uses iCalendar RRULE format ... Libraries: dateutil.rrule (Python), rrule (npm)'). Yet on the create path it is just `rrule: str = "FREQ=DAILY"` with no validator, and on the update path it is `rrule: str | None = None` -- completely free-form. `python-dateutil>=2.8.0` is declared in pyproject.toml (line 17) but is NEVER imported anywhere in app/ (grep for 'dateutil'/'rrulestr' returns zero hits). The service layer (habit_service.create_habit / update_habit) writes the raw attacker string straight into the DB column `String(255)` and the API echoes it back verbatim in every HabitResponse (habits.py:45,74,103). Consequences: (1) garbage like rrule="'; DROP" or rrule="FREQ=WEEKLY;BYDAY=ZZ" or a 255-char junk blob is accepted and persisted; (2) any consumer that actually parses it with dateutil.rrule.rrulestr(...) -- exactly what the spec mandates for computing due-dates -- will raise ValueError/KeyError on the malformed value, turning every scheduling read into a crash; (3) the frontend rrule npm parser is fed untrusted server data. This is a stored-malformed-data injection into the scheduling subsystem.

**Evidence:**

~~~
schemas/habit.py:11  `rrule: str = "FREQ=DAILY"`  and  :18  `rrule: str | None = None`. No field_validator, no pattern, no rrulestr() call anywhere in app/ (grep 'dateutil|rrulestr' -> only the pyproject dependency line). habit_service.py:67 writes it raw: `rrule=data.rrule,`
~~~

**Fix:**

~~~
Validate against dateutil at the schema boundary, e.g.:

```python
from dateutil.rrule import rrulestr
from pydantic import field_validator

class HabitCreate(BaseModel):
    rrule: str = "FREQ=DAILY"
    @field_validator("rrule")
    @classmethod
    def _valid_rrule(cls, v: str) -> str:
        if len(v) > 255:
            raise ValueError("rrule too long")
        try:
            rrulestr(v)            # raises on malformed RRULE
        except (ValueError, KeyError) as e:
            raise ValueError(f"invalid RRULE: {e}") from e
        return v
```
Apply the same validator to HabitUpdate.rrule (it must reject malformed values on partial updates too). This converts a silent 500/stored-corruption into a clean 422 at the edge.
~~~

---

## [LOW] completed_date accepts arbitrary/future dates, corrupting streaks and feeding the calendar blow-up

- **File:** `backend/app/schemas/habit.py:37`
- **Category:** unvalidated-input · **Dimension:** backend-injection-validation · **Verifier confidence:** high

HabitLogCreate.completed_date: date has no bounds. A client can POST /habits/{id}/log with completed_date="9999-12-31" or any far-future/far-past date and it is persisted as-is (habit_service.log_completion:109-114). This is a data-integrity injection: (1) the streak algorithms walk these dates -- compute_current_streak/compute_longest_streak (streak_service.py) and get_analytics (habit_service.py:163-202) treat a year-9999 entry as a real completion, producing nonsense streaks/best-day/weekly stats; (2) it directly enables the calendar/log range abuse -- a real far-future log makes a default-range or wide-range calendar query span millennia; (3) future-dated 'completions' let a user fabricate streaks. Nothing checks the date is not in the future, not absurdly old, nor (per CLAUDE.md's timezone model) within the user's local 'today'.

**Evidence:**

~~~
schemas/habit.py:36-38 ->
class HabitLogCreate(BaseModel):
    completed_date: date
    notes: str | None = None
Written raw at habit_service.py:111 `completed_date=data.completed_date,`. No validator anywhere restricts the date.
~~~

**Fix:**

~~~
Constrain at the schema and/or service:

```python
from datetime import date, timedelta
from pydantic import field_validator

class HabitLogCreate(BaseModel):
    completed_date: date
    notes: str | None = Field(default=None, max_length=2000)
    @field_validator("completed_date")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > date.today() + timedelta(days=1):   # tolerate tz skew
            raise ValueError("completed_date cannot be in the future")
        if v < date(2000, 1, 1):
            raise ValueError("completed_date too far in the past")
        return v
```
Ideally compute 'today' in the user's users.timezone rather than server-local to match the documented daily-reset semantics.
~~~

---

## [LOW] User-supplied timezone is never validated, breaking documented daily-reset and risking later 500s

- **File:** `backend/app/schemas/auth.py:7`
- **Category:** unvalidated-input · **Dimension:** backend-injection-validation · **Verifier confidence:** high

RegisterRequest.timezone: str = "UTC" is a free-form string. It flows unvalidated through register_user(db, data.email, data.password, data.timezone) (auth.py:19) into User(... timezone=tz) (auth_service.py:15) and is stored in users.timezone String(64). CLAUDE.md is explicit that this value is load-bearing: 'User's IANA timezone stored in users.timezone (e.g., America/Los_Angeles)' and 'Daily reset determined by user's midnight, not UTC midnight'. Nothing validates it is a real IANA zone. A client can register with timezone="Mars/Olympus" or timezone="; DROP" or a 64-char blob. The moment any code does ZoneInfo(user.timezone) to compute the user's local 'today' for streaks or daily reset, it raises ZoneInfoNotFoundError -> unhandled 500 (no global handler) for that user on every dashboard load. It is also a stored-bad-data trap that silently corrupts every timezone-dependent computation. (grep confirms zoneinfo/pytz aren't imported yet, so today the value is dead-but-poisoned; it becomes an active crash the instant the documented reset logic is wired up.)

**Evidence:**

~~~
schemas/auth.py:4-7 ->
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    timezone: str = "UTC"
Stored unchecked: auth_service.py:15 `user = User(email=email, password_hash=hash_password(password), timezone=tz)`.
~~~

**Fix:**

~~~
Validate against the IANA database at the boundary:

```python
from zoneinfo import available_timezones
from pydantic import field_validator

class RegisterRequest(BaseModel):
    timezone: str = "UTC"
    @field_validator("timezone")
    @classmethod
    def _valid_tz(cls, v: str) -> str:
        if v not in available_timezones():
            raise ValueError("invalid IANA timezone")
        return v
```
(available_timezones() can be cached.) Reject unknown zones with a 422 instead of persisting them.
~~~

---

## [LOW] description / notes are unbounded Text -- unbounded write (stored-data DoS)

- **File:** `backend/app/schemas/habit.py:9`
- **Category:** schema-gap · **Dimension:** backend-injection-validation · **Verifier confidence:** high

HabitCreate.description, HabitUpdate.description, and HabitLogCreate.notes are all bare str | None with no max_length, and map to Postgres Text columns (models/habit.py:17, models/habit_log.py:23) which are also unbounded. A single authenticated request can submit a multi-megabyte (or larger) description/notes payload that is accepted and persisted in full. Repeated across habits/logs this is an unbounded storage-amplification / stored-data DoS, and bloats every list/calendar/log response returning these fields. FastAPI has no default body-size cap, so nothing upstream limits it either. Low severity (auth required, no RCE/leak) but a real resource-exhaustion gap and trivially fixed.

**Evidence:**

~~~
schemas/habit.py:9 `description: str | None = None` (and :17, and :38 `notes: str | None = None`) -- no Field(max_length=...). Backing columns are unbounded: models/habit.py:17 `description: Mapped[str | None] = mapped_column(Text, nullable=True)`; models/habit_log.py:23 `notes: Mapped[str | None] = mapped_column(Text, nullable=True)`.
~~~

**Fix:**

~~~
Cap free-text fields at the schema layer, e.g. `description: str | None = Field(default=None, max_length=2000)` and `notes: str | None = Field(default=None, max_length=2000)` on all three schemas. Optionally enforce a max request-body size at the ASGI/proxy layer (Starlette middleware or Traefik) as defense in depth.
~~~

---

## [LOW] Heatmap week-bucketing uses getDay() (local) over backend dates, and the missing-day style makes future days look 'completed-adjacent'; calendar query never refetches after a toggle

- **File:** `frontend/src/app/(dashboard)/habits/[id]/page.tsx:19`
- **Category:** cache-invalidation · **Dimension:** frontend-data-fetching · **Verifier confidence:** high

Two coupled issues in HeatmapGrid. (1) It reads ["calendar", id] via useCalendar, but as noted no mutation ever invalidates that key, so completing today never lights up today's cell until the 30s staleTime lapses plus a refetch trigger — the heatmap is effectively frozen for the session. (2) The week-grouping calls new Date(day.date + 'T00:00:00') and groups on d.getDay() === 0 (Sunday). 'T00:00:00' with no offset is parsed in the browser's LOCAL timezone, so for users west of UTC the Date can land on the previous calendar day, shifting which column a date falls into and misaligning the weekday rows of the entire heatmap. The backend returns a contiguous date string list; grouping should be done on the date string, not a timezone-sensitive Date.

**Evidence:**

~~~
// habits/[id]/page.tsx:18-36
const { data: calendar } = useCalendar(habitId);  // ["calendar", id] never invalidated
for (const day of calendar) {
  const d = new Date(day.date + "T00:00:00");      // parsed in LOCAL tz -> can shift a day
  if (d.getDay() === 0 && currentWeek.length > 0) { result.push(currentWeek); currentWeek = []; }
  currentWeek.push(day);
}
~~~

**Fix:**

~~~
1) Invalidate ["calendar", habitId] in the toggle's onSettled/onSuccess (see toggle finding). 2) Group weeks from the date string without constructing a tz-sensitive Date, e.g. compute the weekday with a UTC-stable parse:

const [y, m, dd] = day.date.split('-').map(Number);
const weekday = new Date(Date.UTC(y, m - 1, dd)).getUTCDay(); // stable across client tz
if (weekday === 0 && currentWeek.length > 0) { ... }

This keeps the heatmap columns aligned regardless of the viewer's timezone and makes today's completion appear immediately after the toggle invalidates the calendar key.
~~~

---

## [LOW] Interactive <button> nested inside Next <Link> (anchor) — invalid HTML and broken keyboard activation

- **File:** `frontend/src/components/habits/HabitCard.tsx:22-58`
- **Category:** accessibility · **Dimension:** frontend-react-a11y · **Verifier confidence:** high

The whole card is wrapped in <Link href={`/habits/${habit.id}`}> which, in Next 14 App Router, renders an <a> element. Inside that anchor is the toggle <button> (line 39). The HTML spec forbids interactive content (a button) as a descendant of an <a>; browsers may re-parent the DOM, and the nesting is an accessibility violation. Behaviourally it is broken for keyboard users: the anchor is the focusable target for the card, so pressing Enter navigates to the detail page — there is no keyboard path to the toggle's intended action without a mouse-precise click, and even mouse handling relies on preventDefault/stopPropagation (lines 12-13) which is fragile. Screen readers announce a link that contains a button performing a contradictory action.

**Evidence:**

~~~
<Link href={`/habits/${habit.id}`}>
  <div ...>
    ...
    <button onClick={handleToggle} disabled={toggle.isPending} ...>  // <button> inside <a> — invalid, and Enter navigates instead of toggling
~~~

**Fix:**

~~~
Do not nest the button in the anchor. Make the card a positioned container with the link as a stretched overlay and the button a sibling above it:

<div className="relative ...">
  <Link href={`/habits/${habit.id}`} className="absolute inset-0 z-0" aria-label={habit.name} />
  <div className="relative z-10 flex ...">
    <h3>{habit.name}</h3>
    <button onClick={handleToggle} aria-label={...}>...</button>
  </div>
</div>

The link covers the card for navigation; the button sits on a higher z-index and is independently focusable/operable.
~~~

---

## [LOW] Native confirm() used for destructive archive — no focus management, not stylable, blocks the event loop

- **File:** `frontend/src/app/(dashboard)/habits/[id]/page.tsx:107-111`
- **Category:** accessibility · **Dimension:** frontend-react-a11y · **Verifier confidence:** medium

handleDelete uses the synchronous browser global confirm() to gate an irreversible-feeling 'Archive' action. window.confirm is a hard, blocking, unstyleable dialog: it pauses JS execution, cannot be themed to match the dark UI, gives no control over focus management or labelling, and is increasingly throttled/suppressed by browsers (e.g. when triggered from cross-origin iframes or repeatedly). For a primary destructive flow this is a poor and inaccessible confirmation pattern, and it cannot be tested without stubbing the global. The same applies in spirit to the lack of any in-app confirmation styling.

**Evidence:**

~~~
async function handleDelete() {
  if (!confirm("Archive this habit? You can't undo this.")) return;
  await deleteHabit.mutateAsync(id);
  router.push("/habits");
}
~~~

**Fix:**

~~~
Replace with an in-app accessible confirmation dialog (reuse the dialog primitive recommended for CreateHabitModal): render a role="alertdialog" with aria-labelledby/aria-describedby, focus the cancel button by default, trap focus, and resolve a promise/state on confirm. This gives consistent styling, proper focus handling, and testability.
~~~

---

## [LOW] `/health` is a static literal that never probes Postgres or Redis, and no compose healthcheck targets the app containers — orchestration can route traffic to a broken API

- **File:** `backend/app/main.py:26`
- **Category:** observability · **Dimension:** cross-tests-observability · **Verifier confidence:** high

The only health surface is `GET /health` returning a hardcoded `{"status": "ok"}`. It performs no dependency check, so it returns 200 even when Postgres is unreachable or Redis (used per CLAUDE.md for the token whitelist) is down — i.e. it is a liveness probe masquerading as readiness. Compounding this, `docker-compose.dev.yml` defines healthchecks for `postgres` and `redis` but defines NONE for `habits-api` or `habits-web`, and `habits-web` depends on `habits-api` with a bare `depends_on: - habits-api` (no `condition: service_healthy`). So the frontend container can start and be marked healthy while the API is still failing to connect to its database, and any future load balancer / Traefik (mentioned in CLAUDE.md) keying on container health would happily send live traffic to an API that cannot serve requests. None of this is tested.

**Evidence:**

~~~
backend/app/main.py:26-28 ->
    @app.get("/health")
    async def health():
        return {"status": "ok"}   # never touches DB/Redis
docker-compose.dev.yml -> healthchecks only under `postgres:` (pg_isready) and `redis:` (redis-cli ping); `habits-api:` and `habits-web:` have NO healthcheck; `habits-web` -> `depends_on: - habits-api` (no condition)
~~~

**Fix:**

~~~
Make /health a real readiness check and add container healthchecks. Backend:

```python
@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ok"}
```
(optionally split `/livez` static vs `/readyz` dependency-checked). Compose: add to `habits-api` a `healthcheck` hitting `/health` (e.g. `["CMD","python","-c","import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"]`) and change `habits-web` to `depends_on: { habits-api: { condition: service_healthy } }`. Add a test asserting `/health` returns 503 when the DB session errors.
~~~

---


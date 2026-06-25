# Feature Brainstorm — Ranked Roadmap

> Habit Tracker · 8 ideation lenses → 110 raw ideas → 30 deduped → 3-judge Opus panel (user-impact / feasibility / differentiation) → top 10 mini-specced. ~6.6M tokens.

## Full ranking (avg of 3 judges, 0–10)

| # | Idea | Score |
|---|---|---|
| 1 | Temptation Bundling Pairs | 7 |
| 2 | Anchor Builder (Implementation-Intention Composer) | 6.83 |
| 3 | Never-Miss-Twice Guardrail | 6.67 |
| 4 | Grounded Weekly Reflection | 6.67 |
| 5 | Comeback Mode (Shrink-to-Restart) | 6.5 |
| 6 | Prestige: Graduate a Habit | 6.33 |
| 7 | Pre-Commitment Excuse Trap | 6 |
| 8 | Momentum Physics (XP as Velocity) | 6 |
| 9 | Earned Streak Freezes (Loss-Aversion Insurance) | 5.67 |
| 10 | Interactive Home & Lock Screen Widgets | 5.67 |
| 11 | Always-On Habit Coach Thread | 5.33 |
| 12 | Control Center + Action Button + Back-Tap Logging | 5.33 |
| 13 | Over-Commitment Auditor | 5 |
| 14 | Habit Correlation Graph + Keystone Detector | 5 |
| 15 | Mood-on-Completion + Habit Impact Cards | 5 |
| 16 | Adaptive Reminder Optimizer | 4.67 |
| 17 | Streak Live Activity That Survives the Day | 4.67 |
| 18 | HealthKit Two-Way Auto-Complete | 4.67 |
| 19 | Streak Pacts (1:1 Accountability Partners) | 4.67 |
| 20 | Habit Stacks (Dependency Chains) | 4.33 |
| 21 | Year-in-Habits 'Wrapped' | 4.17 |
| 22 | Conversational Habit Composer | 3.83 |
| 23 | Siri + App Intents Habit Verbs | 3.67 |
| 24 | Streak Sentinel (Progress-Aware Rescue Nudge) | 3.67 |
| 25 | Two-Way Calendar Time-Blocking | 3.33 |
| 26 | Trial-by-Streak (Behavior-Gated Trial) | 3.33 |
| 27 | Accountability Stakes (Opt-In Money on the Line) | 3.33 |
| 28 | Cheer Reactions (Async, No Comments) | 3.17 |
| 29 | Coach Console (B2B-lite) | 2.83 |
| 30 | Universal Importer (Streaks / Way of Life / Habitica / Loop / CSV) | 2.67 |

---

# Top 10 — Mini-Specs

## #1 · Temptation Bundling Pairs — 7/10

_Pair a 'should' habit with a 'want' reward you only allow during it ('true-crime podcast only on the treadmill'), and the app enforces the pairing and reports how much the craving dragged the habit along._

**Problem:** Habit Tracker today is a pure "should-do" logger: every habit is a chore you check off, and the only motivational lever is the streak/reminder nag. There is no mechanism that makes the habit itself attractive in the moment. Behavioral research (Milkman's temptation bundling) shows that pairing a chore with a "want" reward you only permit during the chore raises adherence — and no competitor (Streaks, Habitify, Way of Life) ships this. We also have no data layer that captures *why* a habit got done, so we can never show the user that the craving, not willpower, is doing the work.

**Solution:** Let a habit carry an optional "temptation bundle": a free-text reward (`bundle_reward`, e.g. "true-crime podcast") that is framed as allowed ONLY while performing the habit. Reframe the prompt from nag to invitation ("Time for your treadmill podcast"). When the user logs a completion, capture one extra signal — `reward_indulged` (yes/no) — so we can compute a per-habit "drag-along rate": of completions, how many were powered by the bundled reward. Surface that on the habit detail screen as the headline insight ("The podcast pulled this habit along 18 of 22 days = 82%"). This is a thin additive layer: two nullable columns on `habits`, one nullable column on `habit_logs`, no new tables, no streak-logic changes, and it threads through the existing create/edit form, the log/quick-log flow, the reminder copy, and the detail/analytics view on both iOS and web.

**User story:** As a user who struggles to start a "should" habit, I want to attach a guilty-pleasure reward that I only let myself enjoy while doing that habit, and have the app remind me of the reward instead of nagging me, so that the craving pulls me into the habit — and I want to see, after a few weeks, how often the reward actually dragged the habit along so I know the bundle is working.

**Surfaces:**

- iOS CreateHabitSheet / EditHabitSheet — add 'Temptation bundle' reward field + enable toggle (Features/CreateEdit/)
- iOS QuickLogSheet — when logging a bundled habit, add a single 'Did the reward come along?' toggle (Features/Today/QuickLogSheet.swift)
- iOS HabitRow / TodayView — reframe due-habit subtitle to show the reward as an invitation, not the habit name (Features/Today/)
- iOS HabitDetailView — new 'Bundle pull' stat card showing drag-along rate (Features/HabitDetail/HabitDetailView.swift)
- iOS NotificationScheduler copy — reminder body becomes reward-framed for bundled habits (Slice 06, Core/Notifications/)
- Web CreateHabitModal — reward field + toggle (frontend/src/components/habits/CreateHabitModal.tsx)
- Web HabitCard + habit detail page — reward invitation line + drag-along rate (frontend/src/components/habits/HabitCard.tsx, frontend/src/app/(dashboard)/habits/[id]/page.tsx)
- Backend habits + habit_logs models, schemas, and habits router (backend/app/)

**Data model:** Additive, no new tables. (1) backend/app/models/habit.py — add `bundle_reward: Mapped[str | None] = mapped_column(String(255), nullable=True)` and `bundle_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false', nullable=False)`. (2) backend/app/models/habit_log.py — add `reward_indulged: Mapped[bool | None] = mapped_column(Boolean, nullable=True)` (nullable so non-bundled logs and historical rows stay NULL = 'not applicable'; not defaulted false to keep 'unanswered' distinct from 'no'). (3) One Alembic migration in backend/alembic/versions/ adding all three columns (mirror existing 78e34eb83f13_initial_schema.py style; columns nullable/server_default so it is a safe online add — no backfill, no streak/unique-constraint impact). Schema changes in backend/app/schemas/habit.py: add `bundle_reward`/`bundle_enabled` to HabitCreate, HabitUpdate, HabitResponse; add optional `reward_indulged: bool | None` to HabitLogCreate and HabitLogResponse; add `drag_along_rate: float | None` and `bundled_completions: int` to HabitAnalytics. Mirror types in frontend/src/types/habit.ts (Habit, HabitLog, HabitAnalytics) and the iOS DTOs (DTO+Habits.swift, introduced in slice-03).

**Endpoints:**

- No new routes. Extend existing endpoints in backend/app/routers/habits.py:
- POST /api/v1/habits — accept bundle_reward, bundle_enabled (via HabitCreate)
- PUT /api/v1/habits/{id} — accept bundle_reward, bundle_enabled (via HabitUpdate)
- GET /api/v1/habits and GET /api/v1/habits/{id} — return the two bundle fields in HabitResponse
- POST /api/v1/habits/{id}/log — accept optional reward_indulged in HabitLogCreate (server stores NULL when habit is not bundled or field omitted)
- GET /api/v1/habits/{id}/logs — surface reward_indulged in HabitLogResponse
- GET /api/v1/habits/{id}/analytics — add drag_along_rate (= count(reward_indulged=true) / count(reward_indulged IS NOT NULL)) and bundled_completions, computed in habit_service.get_analytics

**Dependencies:**

- Slice 03 (iOS Today + HabitDetail wired to backend) must be live — bundle fields ride on the same HabitsService/DTO+Habits.swift layer; building before slice 03 means wiring against MockData and re-doing it.
- Backend column add is self-contained but should land before or with the iOS/web UI so the API contract is real (avoid mocking then rework).
- Reward-framed reminder copy depends on Slice 06 (iOS notifications) — treat that piece as a follow-on, not a blocker for the core bundle+drag-along feature.
- Localization (Slice 09) must include the new strings ('Temptation bundle', reward-invitation reminder copy, 'Bundle pull' stat) — Spanish default per SPEC.
- No third-party libraries; reuses existing dateutil.rrule (backend) and Swift Charts / Recharts already in the stack for the stat display.

**Effort:** M · **Success metric:** Primary: among users who create at least one bundled habit, the 30-day completion rate of bundled habits is at least 15 percentage points higher than their non-bundled habits (within-user A/B, computed from existing habit_logs). Supporting/leading: (a) >=30% of active users create at least one temptation bundle within 14 days of the feature shipping; (b) for bundled habits, reward_indulged is answered on >=70% of completions (proves the capture flow is low-friction); (c) median drag_along_rate across bundled habits >0.5. All measurable directly from the new columns plus existing logs — no new analytics infra. · **Suggested slice:** Attach to existing slices, do not create a new top-level slice. Land as one vertical sub-slice with three ordered tasks: (T1) backend additive columns + migration + schema/analytics extension + pytest round-trip (extends Slice 04's backend surface, the natural home for habits-table/streak-adjacent work); (T2) iOS create/edit reward field + QuickLogSheet reward-indulged toggle + HabitDetail 'Bundle pull' card (extends Slice 03's CreateEdit/Today/HabitDetail view-models, since that is where habit CRUD + logging are wired to the backend); (T3) web parity in CreateHabitModal/HabitCard/detail page (extends the existing (dashboard) surface). The reward-framed reminder copy is a small follow-on inside Slice 06. If the team prefers an explicit tracking unit, file it as 'slice-12-temptation-bundling' that depends on 03+04, but its code touches only files those slices already own.

---

## #2 · Anchor Builder (Implementation-Intention Composer) — 6.83/10

_Every habit is created as a structured fill-in-the-blank — 'After I [existing anchor], I will [tiny action] in [location]' — so the cue is a real event, not a clock, and the reminder reads the plan back verbatim._

**Problem:** Habits today are captured as a free-text `name` plus an optional `description`, `color`, and `rrule` (currently locked to `FREQ=DAILY` — see backend/app/schemas/habit.py:11). The only cue the product can offer is a clock-based reminder (slice-06 NotificationScheduler fires `UNCalendarNotificationTrigger` at `reminder_time`). Behavioral science is unambiguous that clock cues are weak and that implementation intentions — "After I [existing routine], I will [tiny action] in [location]" — roughly double follow-through versus a goal alone. Every field needed to express that plan is missing from the data model, so the highest-evidence behavior lever is structurally impossible to capture. Users write vague names ("Exercise"), get a clock ping with no context, and churn.

**Solution:** Restructure the create/edit flow around a fill-in-the-blank composer with three new first-class fields on the habit — anchor_cue (the existing event/routine the new habit piggybacks on), tiny_action (the smallest version of the behavior), and location (where it happens) — keeping the free-text `name` as an auto-derived, editable display label. Persist them as nullable columns so existing habits and the web/iOS clients stay backward-compatible (all three null = a legacy/quick habit). The create surfaces render a structured stepper ("After I ___, I will ___ in ___") that live-previews the assembled sentence and pre-fills `name` from it. The single highest-leverage payoff is at reminder time: slice-06's notification body reads the intention back verbatim ("After your morning coffee, do 1 pushup in the kitchen") instead of a generic "Time for Exercise." Curated anchor suggestions (wake up, morning coffee, brush teeth, lunch, commute home, get into bed) are offered as chips to lower friction. RRULE remains daily-only for now; this change is orthogonal to scheduling. Backend validation trims/length-caps each field; if any of the three are provided, `name` may be auto-generated server-side when omitted.

**User story:** As Armando creating a new habit, I want to compose it as "After I [my morning coffee], I will [do 1 pushup] in [the kitchen]" instead of just typing a name, so that my habit is anchored to a real event I already do and my reminder reads my own plan back to me — making the cue concrete instead of an easily-ignored clock alarm.

**Surfaces:**

- iOS CreateHabitSheet.swift — replace single name field with AnchorBuilder stepper (After/I will/in) + live sentence preview + anchor suggestion chips
- iOS EditHabitSheet.swift — same structured form, prefilled from existing fields
- iOS PersistedHabit @Model (Core/Persistence/PersistedHabit.swift) — add anchorCue/tinyAction/location; WriteOp createHabit/updateHabit payloads carry them
- iOS HabitDetailView + Today/HabitRow — surface the assembled intention sentence as subtitle when present
- iOS NotificationScheduler.swift (slice-06) — build reminder body from the intention sentence, falling back to name
- Web components/habits/CreateHabitModal (+ EditHabitModal) — same three-part composer with preview
- Web components/habits/HabitCard — show intention sentence
- Web types/habit.ts — extend Habit/HabitCreate/HabitUpdate types
- iOS Core/MockData/MockData.swift — give mock habits anchor/action/location so previews look real

**Data model:** Add three nullable text columns to the existing `habits` table (no new table — keep single source of truth, consistent with the computed-streaks philosophy): anchor_cue VARCHAR(120) NULL, tiny_action VARCHAR(120) NULL, location VARCHAR(120) NULL. `name` stays NOT NULL (display label; auto-derived from the three parts on create when omitted). SQLAlchemy: add Mapped[str | None] columns to backend/app/models/habit.py:Habit. Alembic: one additive migration chaining off current head 78e34eb83f13 (down_revision=None today), pure ADD COLUMN, instant on Postgres, no backfill (legacy rows = all three NULL). Pydantic (backend/app/schemas/habit.py): add the three optional fields to HabitCreate, HabitUpdate, and HabitResponse with strip+max-length validators; optionally compute `name` from parts in HabitCreate when blank. iOS PersistedHabit @Model + HabitDTO (slice-03 DTO mirror) gain the three optional String? fields. No index needed (fields are display-only, never filtered/sorted).

**Endpoints:**

- POST /api/v1/habits — extend HabitCreate body to accept anchor_cue, tiny_action, location (all optional); derive name if omitted (existing endpoint, additive)
- PUT /api/v1/habits/{habit_id} — extend HabitUpdate to set/clear the three fields (existing endpoint, additive)
- GET /api/v1/habits and GET /api/v1/habits/{habit_id} — HabitResponse now returns the three fields (additive, no client break)
- GET /api/v1/habits/anchor-suggestions — NEW small read-only endpoint returning a curated localized list of common anchor cues for the chip picker (static/config-backed, no DB)

**Dependencies:**

- Backend slice exists and is migratable: backend/app/models/habit.py, schemas/habit.py, routers/habits.py, services/habit_service.py all present; Alembic head is 78e34eb83f13
- python-dateutil already in backend/pyproject.toml (no new backend deps required)
- iOS create/edit flow must exist first — slice-00 (CreateHabitSheet/EditHabitSheet mock) then slice-03 (wired to backend) and slice-05 (PersistedHabit @Model + WriteOp) — those are prerequisites for the iOS half
- Reminder-copy payoff depends on slice-06 NotificationScheduler (body string assembly); ship that touch with or after slice-06
- Web frontend create-habit components are specified in CLAUDE.md but not yet built in frontend/src — the web half lands whenever those CreateHabitModal/HabitCard components are implemented
- No new third-party libraries; no auth/schema-on-existing-columns changes (additive columns only)

**Effort:** M · **Success metric:** Primary: >=60% of habits created in the 4 weeks after launch include at least one populated anchor field (anchor_cue, tiny_action, or location) — measured by SQL count on the habits table. Secondary (behavioral proof the lever works): cohort of habits WITH a populated anchor_cue shows a higher 14-day completion rate (completed days / scheduled days from habit_logs) than habits without one, target >=10 percentage-point lift. · **Suggested slice:** Attaches primarily to existing slice-03 (iOS Today + CreateEdit wired to backend) — that slice already rewrites CreateHabitSheet/EditHabitSheet against real endpoints, so the structured composer rides in there alongside a small backend-additive task (new migration + schema/DTO fields + anchor-suggestions endpoint, naturally grouped with slice-04 backend work). The reminder-copy payoff is a 1-task addition to slice-06 (NotificationScheduler body assembly). Web composer lands with the existing frontend create-habit components (no new slice needed). A dedicated new slice is NOT warranted — this is foundational data-model + create-flow surgery that threads through slices already in the 00-11 plan rather than standing alone.

---

## #3 · Never-Miss-Twice Guardrail — 6.67/10

_Treat one miss as normal but detect the at-risk second consecutive day as a red-alert state, escalating the nudge and opening a 60-second get-back-on-track flow at the exact cliff edge._

**Problem:** Habits are abandoned not at the first miss but at the second consecutive one — once a streak resets to zero, motivation collapses. The current product treats every non-completion identically: the streak silently goes to 0 and the daily reminder (Slice 06) fires the same generic nudge whether the user is cruising on a 40-day streak or standing on the cliff edge of their first missed day. The app computes consecutive runs (`streak_service.py`) but has no concept of a "grace" state after a single miss, no escalated intervention at the highest-risk moment, and no low-friction path back. It surfaces the streak number but does nothing at the exact point where abandonment statistically happens.

**Solution:** Add a per-habit streak STATE MACHINE computed on top of existing logs: on_track (last scheduled day done or today still open) → at_risk (exactly the most-recent scheduled day was missed; streak frozen, not yet broken) → broken (two+ consecutive scheduled days missed). "Scheduled day" uses the RRULE primitives from Slice 04 (`schedule.previous_scheduled_date` / `is_scheduled`), so a weekday habit isn't flagged at-risk over a weekend. The state is exposed on the habit detail payload and drives three behaviors: (1) a red-alert visual treatment on the at-risk habit (iOS HabitRow + web HabitCard); (2) an escalated, differently-worded notification ("Don't break your 40-day streak — one tap saves it") that fires on the at_risk day instead of the normal reminder, reusing the Slice 06 NotificationScheduler + "Mark done" action; (3) a 60-second "Get back on track" recovery sheet that opens from the at-risk habit or the escalated notification, letting the user log today in one tap and optionally backfill yesterday with an "excused" flag (travel/sick) that preserves the streak without falsifying the completion record. Excused days are stored explicitly so streak math can bridge a single planned gap. A daily scheduled task recomputes states and enqueues escalated nudges; everything else is computed on read.

**User story:** As a habit-tracker user who just missed a day for the first time, I want the app to recognize that single miss as the danger zone — show me a clear red alert, send me a sharper reminder, and give me a 60-second one-tap path to log today (and excuse yesterday if life got in the way) — so that one slip never snowballs into a broken streak and an abandoned habit.

**Surfaces:**

- iOS Today view — HabitRow gains an at_risk red-alert state (badge, color, subtle pulse), tapping opens the recovery sheet (Features/Today/, scaffolded in Slice 03/05)
- iOS recovery flow — new GetBackOnTrackSheet (Features/Today/ or new Features/Recovery/): one-tap log today + optional 'excuse yesterday' with reason chips
- iOS notifications — escalated at_risk notification copy + deep link to recovery sheet, via Core/Notifications/NotificationScheduler + NotificationRouter (Slice 06)
- iOS HabitDetail — show current state and excused days on the heatmap (distinct from completed/missed)
- Web HabitCard (frontend/src/components/habits/) — at_risk red-alert styling mirroring iOS
- Web habit detail page — recovery CTA + excused-day rendering on the SVG heatmap
- Backend streak_service / new guardrail_service — state-machine computation
- Backend scheduled task — daily state recompute + escalated-nudge enqueue (extends the analytics daily task referenced in CLAUDE.md)
- Web admin logs editor (Slice 10) — view/clear excused flags when fixing bad data

**Data model:** ["habit_logs: add status column — enum('completed','excused') NOT NULL DEFAULT 'completed'. An 'excused' row marks a scheduled day intentionally skipped (sick/travel) that bridges the streak. Keeps the existing UNIQUE(habit_id, completed_date); a date is either completed, excused, or absent.", "habit_logs (optional): add excuse_reason VARCHAR(50) NULL for analytics on why days were excused.", "No streaks/state table — guardrail state is computed on read from logs + RRULE, consistent with the project's 'computed streaks, single source of truth' decision (CLAUDE.md). Cache in Redis (DB#2) only if the daily recompute proves slow.", "Optional habits.guardrail_enabled BOOLEAN DEFAULT true so a user can opt a specific habit out of escalated nudging.", "Alembic migration adds the status column + a partial/covering index assist on (habit_id, completed_date, status); reuses the composite index from Slice 04."]

**Endpoints:**

- GET /api/v1/habits/{habit_id} — extend HabitDetailResponse with guardrail_state: 'on_track'|'at_risk'|'broken' and at_risk_since: date|null
- GET /api/v1/habits — include lightweight guardrail_state per habit so Today/HabitCard can render red-alert without N detail calls
- POST /api/v1/habits/{habit_id}/recover — body { log_today: bool, excuse_date: date|null, excuse_reason: str|null }; one call powering the 60-second flow: logs today and/or writes an excused row for the missed day; returns updated streak + guardrail_state
- POST /api/v1/habits/{habit_id}/log — extend body with optional status:'completed'|'excused' (default 'completed') and completed_date so backfill/excuse reuses the existing endpoint
- DELETE /api/v1/habits/{habit_id}/logs/{date} — already-implied unmark path; ensure it clears excused rows too (admin + user undo)
- GET /api/v1/analytics/at-risk — (admin/metrics, Slice 10) count of habits currently in at_risk/broken for the daily-task + dashboard

**Dependencies:**

- Slice 04 (Backend RRULE-aware streaks) — HARD dependency: needs schedule.is_scheduled / previous_scheduled_date to define the 'most recent scheduled day' correctly across daily/weekday/weekly RRULEs; the state machine is meaningless without it
- Slice 06 (iOS local notifications) — HARD dependency for the escalated-nudge rail: reuses NotificationScheduler, the MARK_DONE category, and NotificationRouter; adds an at_risk-priority variant + deep link
- Slice 03/05 (iOS Today + offline cache) — the HabitRow and SwiftData PersistedHabit the red-alert state and recovery sheet attach to; offline recover writes go through the Slice 05 write queue
- Slice 01 (mobile auth + Redis whitelist) — Redis (DB#2) available if state caching is needed
- Daily scheduled task runner — the analytics daily-refresh task (CLAUDE.md 'refreshed daily via scheduled task') hosts the recompute + nudge enqueue; if none exists yet, a small APScheduler/cron addition is in scope
- Web Slice 10 (admin) — soft: surfaces excused-flag management and the at-risk metric, but the guardrail ships without it

**Effort:** L · **Success metric:** Primary: streak-recovery rate — of all habit-instances that enter the at_risk state, the percentage that log a completion within their next scheduled day (i.e., return to on_track instead of going broken). Target a meaningful lift versus the pre-feature baseline (instrument the at_risk→on_track vs at_risk→broken transition counts for ~2–4 weeks before/after; aim for a >=15 percentage-point absolute increase in recovery rate). Guardrail metric: 28-day habit retention (habits still being logged 28 days after creation) must not regress and ideally improves, confirming reduced abandonment rather than just more excused days. · **Suggested slice:** New Slice 12 — "Never-Miss-Twice Guardrail." It is a distinct vertical feature (state machine + escalated nudge + recovery flow + excused-day data model) that cuts across backend, iOS, and web, and sits downstream of Slices 04 and 06 in the dependency graph (after CHECKPOINT D, feature-complete dogfood). It does not fit inside any existing slice: Slice 04 is pure streak-correctness math, Slice 06 is generic per-habit reminders. Sequence it after Slice 06 and before/parallel to Slice 10. Internal task order: (1) backend status='excused' migration + state-machine in a new guardrail_service with parametrized RED tests reusing schedule.py; (2) extend detail/list/recover endpoints; (3) daily recompute + escalated-nudge enqueue; (4) iOS at_risk HabitRow + GetBackOnTrackSheet + notification variant; (5) web HabitCard/detail red-alert + excused heatmap rendering.

---

## #4 · Grounded Weekly Reflection — 6.67/10

_Every Sunday Claude reads your real week of logs and writes a 4-sentence recap citing your actual numbers, surfacing the cross-habit pattern a heatmap can't say out loud._

**Problem:** Tracker shows single-habit checkmarks, never the cross-habit pattern. No reflective surface, LLM dep, account analytics, or scheduler exist.

**Solution:** Sunday job builds a deterministic numbers-only WeeklySummary (streaks via streak_service.py, rates, cross-habit co-occurrence) and sends only that to Claude for a 4-sentence recap citing numbers verbatim: cheap, no hallucination. Stored in weekly_reflections, read-only web+iOS.

**User story:** As a user who logged a full week, I want a Sunday recap citing my numbers and a cross-habit pattern.

**Surfaces:**

- reflections.py, reflection_service.py, claude_service.py, weekly_reflection.py job
- iOS card
- web analytics panel
- slice-10 KPI

**Data model:** weekly_reflections: user_id FK, week_start DATE, summary_json JSONB, body TEXT, status; UNIQUE(user_id,week_start); from habit_logs only

**Endpoints:**

- GET /reflections/current
- GET /reflections
- POST /reflections/regenerate
- internal weekly batch

**Dependencies:**

- Anthropic SDK (new)
- scheduler (none, new infra)
- slice-04
- slice-10
- slice-06
- Redis optional

**Effort:** M · **Success metric:** 40 percent view within 48h; 0 numeric hallucinations; under 1 cent/user/wk; 99 percent generated in 6h · **Suggested slice:** NEW slice-12; no 00-11 owns LLM/scheduler/cross-habit; after 04+10, feeds 06; first task summary builder+table

---

## #5 · Comeback Mode (Shrink-to-Restart) — 6.5/10

_Returning after a lapse drops the habit to its 2-minute floor, archives the lost streak instead of zeroing it in your face, and starts a fresh 'comeback' chain to kill the shame barrier._

**Problem:** The single biggest churn moment in habit apps is the broken streak. Today, the app computes the current streak on-the-fly in `backend/app/services/streak_service.py` (`current_streak_from_dates`): miss one calendar day and the count silently snaps from N back to 0 (or 1) the next time you log. The web `HabitCard.tsx` then shows a stark "0 day streak" beside the still-intact "longest / best", which reads as a punishment and an erasure of prior effort. There is no concept of a lapse, no protected re-entry, and no reduced commitment — the user faces the full habit and a zeroed counter at exactly the lowest-motivation moment, which is when people delete the habit (or the whole app). Nothing in the current schema, API, web UI, or iOS scaffold acknowledges a return-after-a-gap as a distinct, supportable event.

**Solution:** Introduce a first-class "lapse + comeback" lifecycle layered on top of the existing computed-streak engine (no stored streaks table is added; we keep single-source-of-truth from `habit_logs`).

1. Detect a lapse: a habit is "lapsed" when the gap between today and the last completed *scheduled* date exceeds a per-habit `lapse_grace_days` threshold (default 1; reuses slice-04's RRULE `is_scheduled`/`previous_scheduled_date` so weekday habits don't false-trip on weekends).
2. Archive, don't zero: when the user returns and logs after a lapse, the pre-lapse run is frozen as a `streak_chapter` row (start_date, end_date, length) — the "eulogy" — instead of being thrown away. The streak engine gains a `comeback_started_at` anchor per habit; the *current* streak is computed only from logs on/after that anchor, so a fresh "comeback chain" starts at 1, while the archived chapters and `longest_streak` (computed across all logs) remain visible and untouched.
3. Shrink-to-restart: each habit gets an optional `floor_goal` (default "2-minute version", free-text + a boolean `comeback_active`). On comeback start the API returns the floor variant so all surfaces can render the easier ask ("Meditate — just 2 minutes today") until the comeback chain reaches a `comeback_exit_streak` (default 3), after which it auto-restores the full habit and clears `comeback_active`.
4. Surface it gently: instead of "0 day streak", surfaces show "Comeback: day 2 · your best was 41 🪦 archived, not lost". A returning-user nudge (web toast / iOS local notification, hooking the existing slice-06 NotificationScheduler) frames re-entry positively.

Mechanically this is: new nullable columns on `habits`, one new `streak_chapters` table, a `comeback_service.py` that wraps the existing `compute_current_streak`, three additive endpoints, and rendering changes on web `HabitCard`/detail and iOS `TodayView`/`HabitDetail` + `StreakComputer` port. Logging itself is unchanged (`POST /habits/{id}/log` stays the write path); comeback transitions are derived/triggered server-side on log + on read.

**User story:** As someone who missed several days of a habit I cared about, when I open the app and tap to log again, I want the app to drop the habit to its tiny 2-minute version, keep my lost streak as a saved "chapter" instead of flashing 0 in my face, and start a fresh comeback count from day 1 — so that returning feels encouraging instead of shameful and I actually resume the habit instead of deleting it.

**Surfaces:**

- Backend — backend/app/services/streak_service.py (wrapped, not replaced) + new backend/app/services/comeback_service.py
- Backend — backend/app/models/habit.py (new comeback columns) + new backend/app/models/streak_chapter.py
- Backend — backend/app/schemas/habit.py (extend HabitResponse with comeback fields) + new ComebackState/StreakChapter schemas
- Backend — backend/app/routers/habits.py (3 additive endpoints, comeback derivation on GET + on POST /log)
- Backend — new Alembic migration in backend/alembic/versions/ (columns + streak_chapters table + composite-friendly index)
- Web — frontend/src/components/habits/HabitCard.tsx (comeback badge replacing the stark '0 day streak')
- Web — frontend/src/app/(dashboard)/habits/[id]/page.tsx + a new StreakChapters/Eulogy component (chapter timeline)
- Web — frontend/src/hooks/useHabits.ts + frontend/src/types/habit.ts (comeback fields + useComebackChapters query)
- iOS — ios Features/Today (TodayView/HabitRow + TodayViewModel) renders comeback badge + floor goal
- iOS — ios Features/HabitDetail (chapter eulogy timeline) + Core/Persistence StreakComputer.swift + PersistedHabit fields (mirrors backend; respects offline write queue from slice-05)
- iOS — Core/Notifications NotificationScheduler (reuse slice-06) for the positive comeback nudge

**Data model:** Migrate `habits` (table `habits`, model `backend/app/models/habit.py`) — add nullable columns, all backward-compatible: `comeback_anchor_date DATE NULL` (current-streak computation start; NULL = no active comeback), `comeback_active BOOLEAN NOT NULL DEFAULT false`, `floor_goal VARCHAR(255) NULL` (the shrunk 2-minute ask), `lapse_grace_days SMALLINT NOT NULL DEFAULT 1`, `comeback_exit_streak SMALLINT NOT NULL DEFAULT 3`. No `streaks` table is introduced — current/longest streaks stay computed from `habit_logs` per the existing architecture; `comeback_anchor_date` simply narrows the date window fed to `current_streak_from_dates`.

New table `streak_chapters` (model `backend/app/models/streak_chapter.py`, mirrors UUIDMixin/TimestampMixin style of existing models): `id UUID PK`, `habit_id UUID FK -> habits.id ON DELETE CASCADE (indexed)`, `start_date DATE NOT NULL`, `end_date DATE NOT NULL`, `length INT NOT NULL`, `kind VARCHAR(20) NOT NULL DEFAULT 'streak'` (room for future 'comeback'), `created_at TIMESTAMPTZ`. Index `(habit_id, end_date DESC)` for fast chapter timelines; composes with the slice-04 `(habit_id, completed_date DESC)` index already planned on `habit_logs`. A chapter is written exactly once, server-side, at the moment a lapse-then-return is detected (idempotent on `(habit_id, start_date, end_date)`).

Pydantic (`backend/app/schemas/habit.py`): extend `HabitResponse` with `comeback_active: bool`, `floor_goal: str | None`, `comeback_streak: int` (days since anchor), `lapsed: bool`, and `last_chapter_length: int | None` (for the eulogy line). Add `StreakChapter` and `ComebackState` response models. iOS `PersistedHabit` (slice-05) and `frontend/src/types/habit.ts` mirror these fields exactly so the offline `StreakComputer.swift` reproduces server values.

**Endpoints:**

- GET /api/v1/habits and GET /api/v1/habits/{id} — UNCHANGED routes, EXTENDED response: HabitResponse now includes comeback_active, floor_goal, comeback_streak, lapsed, last_chapter_length (computed in comeback_service, replacing the bare current_streak when a comeback is active)
- POST /api/v1/habits/{id}/log — UNCHANGED contract; side-effect added: on log after a detected lapse, server writes a streak_chapter, sets comeback_anchor_date=today, comeback_active=true; on reaching comeback_exit_streak it auto-clears comeback_active and floor_goal
- GET /api/v1/habits/{id}/chapters — NEW: returns list[StreakChapter] (the eulogy timeline) for the detail screen
- POST /api/v1/habits/{id}/comeback/dismiss — NEW: user opts out of comeback framing for this habit (sets comeback_active=false, keeps chapters); idempotent
- PATCH /api/v1/habits/{id} (via existing HabitUpdate on PUT) — EXTENDED: accept floor_goal, lapse_grace_days, comeback_exit_streak so the user can tune their floor and grace period

**Dependencies:**

- slice-04 (backend RRULE-aware streaks) — HARD dependency: comeback lapse detection must use schedule.is_scheduled/previous_scheduled_date so weekday/weekly habits don't false-trigger a lapse on off-days; building on the naive day-walker would produce wrong comebacks
- slice-03 (iOS Today + HabitDetail wired online) — iOS surfaces must exist; today iOS is a 3-file scaffold, so the comeback badge/eulogy have nowhere to render until slice-03 lands the real views + HabitsService/DTOs
- slice-05 (iOS offline cache + StreakComputer + WriteQueue) — SOFT but strong: the offline StreakComputer.swift must mirror comeback_anchor_date logic, and comeback transitions triggered by an offline log must reconcile through SyncEngine; without it, iOS comeback state diverges offline
- slice-06 (iOS notifications) — SOFT: reused (not blocking) for the positive returning-user nudge via the existing NotificationScheduler
- Alembic + async SQLAlchemy 2.0 migration tooling (already in stack) for the additive columns + streak_chapters table

**Effort:** L · **Success metric:** Primary (retention / anti-churn): among habits that experience a lapse (gap > lapse_grace_days), the 14-day reactivation rate — share that gets at least one new log within 14 days of the lapse — rises by ≥30% relative to the pre-feature baseline (measured as a before/after cohort on the same user base, since habit_logs already provides the full timeline to compute both). Guardrail: habit deletion/archival (DELETE /api/v1/habits/{id}) within 7 days of a lapse drops by ≥20%, and overall daily logging volume does not regress. Instrumented server-side from existing habit_logs + the new streak_chapters table (no new analytics infra required); a chapter row is the clean event marker for "a streak ended," and a subsequent log on/after comeback_anchor_date is the "came back" marker. · **Suggested slice:** Attach the CORE logic to slice-04 (backend RRULE-aware streaks) since that slice already rewrites and owns streak computation and is where lapse detection naturally lives — but the feature is cross-surface (backend + web + iOS) and larger than slice-04's scope, so it needs its OWN new vertical slice: propose slice-12-comeback-mode.md, sequenced AFTER slice-04 (streak engine) and slice-05 (iOS offline + StreakComputer), optionally pulling slice-06 for the nudge. Recommended thin first increment to de-risk: backend-only Walking Skeleton — add the columns + streak_chapters table + comeback_service wrapping compute_current_streak + the extended HabitResponse + GET /chapters, fully unit-tested (mirroring slice-04's parametrized RRULE×log-pattern test style), with NO UI. Verify via curl that a lapse-then-log produces a chapter and a comeback_streak=1, daily-habit behavior is unchanged when there's no lapse, and longest_streak is preserved. Then layer web HabitCard/detail rendering, then iOS once slice-03/05 land. This keeps it an incremental-implementation vertical slice rather than a big-bang three-surface change.

---

## #6 · Prestige: Graduate a Habit — 6.33/10

_Once a habit is deeply automatic, you can graduate it — it leaves the daily list, mints a permanent emblem, frees a slot, and keeps optional rare spot-checks to stay honest._

**Problem:** The product's north star is automaticity — a habit so ingrained you no longer need to track it. But the app has no exit: every habit lives in the Today list forever (`list_habits` returns all rows where `archived_at IS NULL`), so mastered habits compete for attention with habits that still need scaffolding, and the only "exit" is `DELETE` (soft-archive via `archived_at`), which feels like quitting and discards the win. There is no way to celebrate reaching automaticity, no way to declutter Today toward habits that still need work, and no honesty mechanism to confirm a "graduated" habit is actually still being performed. Today's data model has exactly two terminal states for a habit — active or archived — and neither represents "mastered, retired with honor."

**Solution:** Add a third habit lifecycle state, "graduated," distinct from active and archived. When a habit's computed `current_streak` crosses an automaticity threshold (default 66 consecutive scheduled completions, the commonly cited median for automaticity; configurable per habit), the HabitDetail surface unlocks a "Graduate" action. Graduating sets `habits.graduated_at` (mirroring the existing `archived_at` nullable-timestamp pattern), snapshots the milestone into a new `habit_emblem` row (habit name, color, streak length, total completions, dates), removes the habit from the Today/daily list and its slot count, and presents a triumphant "minted emblem" moment. Emblems live on a read-only "Hall of Habits" shelf. To keep it honest, graduation optionally enables rare randomized spot-checks: a low-frequency reminder (reusing the iOS notifications surface from slice-06) asks "still doing this?" If confirmed, the emblem keeps its shine; if the user reports a lapse (or ignores N consecutive spot-checks), the habit can be un-graduated — returned to the active daily list with its history intact — so the system never lies about mastery. Streaks remain computed, not stored: eligibility is just `compute_current_streak(...) >= threshold`, so this rides the existing single-source-of-truth architecture with zero new streak bookkeeping. Graduation frees attention and (optionally) a soft slot, decluttering Today toward habits that still need the scaffolding.

**User story:** As Armando, when I have meditated daily for 66 days straight and it has become as automatic as brushing my teeth, I want to graduate the habit — celebrate the win, remove it from my Today list so it stops competing with habits I'm still building, keep a permanent emblem of the achievement, and agree to the occasional spot-check so I stay honest — instead of either tracking it forever or deleting it like I gave up.

**Surfaces:**

- iOS Features/Today (TodayView + TodayViewModel): graduated habits drop off the daily list; the 'X of Y done today' hero and any slot count exclude them
- iOS Features/HabitDetail (HabitDetailView + HabitDetailViewModel): shows automaticity progress toward threshold; unlocks the 'Graduate' action + confirmation sheet once eligible; offers 'Return to daily' to un-graduate
- iOS new Features/Emblems (Hall of Habits shelf) — reachable from Settings or Today; read-only grid of minted emblems
- iOS Features/Settings: toggle spot-checks on/off, set spot-check cadence; per-habit automaticity threshold override lives in CreateEdit
- iOS Notifications (slice-06 NotificationScheduler/ReminderManager): schedules rare randomized spot-check prompts and handles the confirm/lapse response
- Web (dashboard)/habits + habits/[id]: graduated habits move out of the active grid into a 'Graduated' section/badge; read-mostly (graduate/return actions can be web-deferred to a later pass)
- Backend app/routers/habits.py + services/habit_service.py + streak_service.py: eligibility gate, graduate/ungraduate transitions, list filtering, emblem creation
- SwiftData offline cache (slice-05): graduated_at + emblem mirrored locally; graduate/ungraduate enqueued through the existing WriteQueue/SyncEngine so it works offline

**Data model:** Migrate via Alembic (one named migration, additive — no changes to existing columns, honoring SPEC §7 'Ask first' for column edits). (1) ADD COLUMN habits.graduated_at TIMESTAMPTZ NULL — third lifecycle state alongside the existing archived_at; a habit is 'active' when both are NULL, 'graduated' when graduated_at IS NOT NULL and archived_at IS NULL, 'archived' when archived_at IS NOT NULL. (2) ADD COLUMN habits.automaticity_threshold INT NOT NULL DEFAULT 66 — per-habit streak length required to graduate (override in CreateEdit). (3) ADD COLUMN habits.spot_check_enabled BOOLEAN NOT NULL DEFAULT true and habits.spot_check_cadence_days INT NOT NULL DEFAULT 30. (4) NEW TABLE habit_emblems (id UUID PK, habit_id UUID FK->habits ON DELETE CASCADE, user_id UUID FK->users, name VARCHAR(255), color VARCHAR(7), graduated_streak INT, total_completions INT, first_logged_date DATE NULL, graduated_at TIMESTAMPTZ, created_at TIMESTAMPTZ; index on user_id) — immutable snapshot so the emblem survives even if the habit is later deleted or its logs change. (5) NEW TABLE spot_checks (id UUID PK, habit_id UUID FK->habits ON DELETE CASCADE, prompted_on DATE, status VARCHAR(16) DEFAULT 'pending' [pending|confirmed|lapsed|missed], responded_at TIMESTAMPTZ NULL; unique(habit_id, prompted_on)) — drives the honesty loop and the un-graduate decision (N consecutive missed/lapsed -> auto-return to active). No streaks table is introduced; eligibility stays computed from habit_logs via the existing streak_service. Add HabitResponse fields: lifecycle_state (str), automaticity_progress (int, = min(current_streak, threshold)), is_graduation_eligible (bool), graduated_at (datetime|None).

**Endpoints:**

- POST /api/v1/habits/{habit_id}/graduate — guarded by compute_current_streak(...) >= habit.automaticity_threshold; sets graduated_at, creates habit_emblems snapshot, returns the new emblem + updated HabitResponse; 409 if not yet eligible, 404 if not owner
- POST /api/v1/habits/{habit_id}/ungraduate — clears graduated_at, returns habit to the active daily list with logs intact (the 'lapse'/manual-return path); 409 if not currently graduated
- GET /api/v1/habits?state=active|graduated|archived — extend list_habits with a state filter (default active = current behavior: archived_at IS NULL AND graduated_at IS NULL) so Today excludes graduated habits without breaking the existing contract
- GET /api/v1/emblems — list the authenticated user's minted emblems for the Hall of Habits shelf (HabitEmblemResponse)
- POST /api/v1/habits/{habit_id}/spot-check/{prompted_on} — record a spot-check response {status: confirmed|lapsed}; on 'lapsed' or N consecutive missed it triggers ungraduate; backs the notification action
- PATCH /api/v1/habits/{habit_id} — extend existing HabitUpdate to accept automaticity_threshold, spot_check_enabled, spot_check_cadence_days (additive fields, no contract break)

**Dependencies:**

- Slice 04 (RRULE-aware streaks) — HARD dependency: 'deeply automatic' is gated on compute_current_streak >= threshold; for any non-daily habit the streak must skip off-days correctly (slice-04's schedule.py) or eligibility fires wrongly. Today rrule is validated to FREQ=DAILY only, so daily-only graduation could ship before slice-04, but the threshold gate is only trustworthy across schedules after slice-04.
- Slice 03 (iOS Today + HabitDetail online) — the Graduate action and progress UI attach to HabitDetailViewModel/TodayViewModel which slice-03 creates.
- Slice 05 (iOS offline cache + WriteQueue/SyncEngine) — to graduate/ungraduate offline and mirror graduated_at + emblems in SwiftData; graduation can ship online-only first and gain offline support after 05.
- Slice 06 (iOS local notifications) — required for the optional rare spot-check prompts and their confirm/lapse actions; if 06 is not done, ship graduation with spot-checks defaulted off.
- Alembic + database-migrations skill for the additive migration; existing dateutil for scheduled-date math reused from slice-04.

**Effort:** L · **Success metric:** Primary (behavioral): at least 30% of habits that reach the automaticity threshold are graduated (rather than left tracked or deleted) within 14 days of becoming eligible — proving the triumphant exit is preferred over tracking-forever or quitting. Guardrail (honesty): of graduated habits with spot-checks enabled, >=80% of fired spot-checks receive a 'confirmed' response, and <10% of graduations are reversed via ungraduate within 90 days (a higher reversal rate means the threshold is too low / graduation is premature). Instrumented via the admin metrics surface (slice-10): graduations/day and eligible-but-not-graduated count. · **Suggested slice:** New slice-12 ('Habit graduation + emblems + honesty spot-checks'). It is a coherent vertical (backend lifecycle/state + iOS Today/HabitDetail/Emblems UI + light web read) that does not fit cleanly inside an existing slice: slice-03 is online CRUD, slice-04 is streak correctness, slice-05 is offline, slice-06 is notifications — graduation spans the seams of all four. Sequence it after slice-06 (so spot-checks have a notifications home) and strictly after slice-04 (so the automaticity gate is schedule-correct). Split into three vertical tasks: 12.1 backend (migration + graduate/ungraduate/list-filter/emblems endpoints + RED tests in backend/tests, gate reuses streak_service), 12.2 iOS graduate flow (HabitDetail eligibility + Graduate sheet + Today exit + Emblems shelf, mirrored through WriteQueue), 12.3 spot-check honesty loop (scheduled prompt via slice-06 NotificationScheduler + confirm/lapse -> ungraduate). Web 'Graduated' section is a small additive pass that can attach to slice-10 (web admin/dashboard work) rather than block slice-12.

---

## #7 · Pre-Commitment Excuse Trap — 6/10

_At creation the user names the excuse they're most likely to use to skip; that exact excuse is shown back to them the instant they tap 'skip.'_

**Problem:** Skipping a habit today is frictionless and consequence-free: the current app has no "skip" affordance at all — a missed day is simply the absence of a `habit_logs` row (confirmed in `backend/app/services/habit_service.py`: only `log_completion`/`remove_completion` exist, and `habit_logs` has a `(habit_id, completed_date)` unique constraint with a `notes` column but no status). Users rationalize skips in the moment ("too tired", "no time") with nothing pushing back. Generic motivational copy is ignored because it isn't *their* rationalization. There is no Ulysses-contract / pre-commitment mechanism anywhere in the product, and the per-habit "why" the idea references does not exist yet — `habits` only has name/description/color/rrule.

**Solution:** At habit creation, the user names the single excuse they are most likely to use to skip (e.g. "I'm too tired") and, as the values-mirroring sibling, their "why" they want this habit (e.g. "So I can keep up with my kids"). Both are stored on the habit. We introduce an explicit, lightweight Skip action (which does not exist today) on the iOS Today row and web habit card. The instant the user taps Skip, an interstitial confirm shows their own pre-committed excuse verbatim ("You said you'd skip with: 'I'm too tired'") alongside their "why", with two choices: "Do it anyway" (logs completion) or "Skip anyway" (records a skip with reason). This is a near-zero-UI Ulysses contract: the friction is purely psychological — confronting your own words at the decision point. The "why" mirror reinforces values at the same moment. Skips are recorded as first-class events (not just absence) so they can be counted for the success metric and shown on the detail/heatmap. To avoid bloating the binary completion model, skip is added as a `status` discriminator on the existing `habit_logs` row, preserving the one-row-per-day invariant and the unique constraint, so the computed-streak walk (slice-04) treats `status='skipped'` as a break with an attached reason rather than a silent gap.

**User story:** As Armando logging from the iOS Today screen, when I tap Skip on a habit I'm about to bail on, I want to be shown the exact excuse I predicted I'd use plus the reason I started this habit, so I'm forced to confront my own rationalization and decide deliberately — making it meaningfully harder to skip on autopilot.

**Surfaces:**

- iOS — CreateHabitSheet/EditHabitSheet (slice-00/03): two new fields, 'Excuse I'm most likely to use' and 'My why', captured at create/edit
- iOS — Today HabitRow + new SkipExcuseSheet/QuickLogSheet (slice-00/03): adds a Skip affordance (swipe action or long-press menu) that currently does not exist, then presents the excuse-trap interstitial with Do-it-anyway / Skip-anyway
- iOS — HabitDetail StatsView + HeatmapCanvas: render skipped days distinctly and list skip reasons in log history
- iOS — Home Screen widget (slice-07) and Live Activity (slice-08): NOT in scope for the trap interstitial (read-only / minimal surfaces); widget skip stays a plain no-op for v1
- Web — CreateHabitModal / habit card on (dashboard)/habits (existing Next.js): mirror the two creation fields and a Skip button with the same excuse-trap confirm dialog
- Web — habit detail page: show skip markers + reasons
- Backend — habits router/schema/model + new skip endpoint + streak_service (slice-04) so skips break streaks with a recorded reason instead of being indistinguishable from missed days

**Data model:** Two additive nullable columns on `habits` (Alembic migration, mirroring existing String/Text columns in `app/models/habit.py`): `anticipated_excuse VARCHAR(280) NULL` and `motivation_why VARCHAR(280) NULL`. On `habit_logs` (`app/models/habit_log.py`), add `status VARCHAR(16) NOT NULL DEFAULT 'completed'` constrained to {'completed','skipped'} (CHECK or PG enum), and reuse the existing `notes TEXT` column to store the optional free-text skip reason. The existing `UNIQUE(habit_id, completed_date)` constraint is preserved and now means 'one outcome per day' (completed OR skipped), which the computed-streak algorithm (no streaks table — streaks are computed per CLAUDE.md) reads: a row with status='skipped' is an explicit break. Backfill is trivial — all existing rows are completions, so DEFAULT 'completed' is correct; migration is reversible (drop columns). No new table needed; rejected a separate `habit_skips` table because it would duplicate the per-day uniqueness logic and complicate the streak walk.

**Endpoints:**

- POST /api/v1/habits/{habit_id}/skip — new; body {completed_date: date, reason?: str}; writes a habit_logs row with status='skipped' (409 if an outcome already exists for that date, matching existing log_completion conflict handling); returns HabitLogResponse
- PUT/POST /api/v1/habits and PUT /api/v1/habits/{habit_id} — extend HabitCreate/HabitUpdate/HabitResponse schemas (app/schemas/habit.py) with optional anticipated_excuse and motivation_why (max_length 280) so the excuse/why round-trip at create/edit
- GET /api/v1/habits/{habit_id} and GET /api/v1/habits/{habit_id}/logs and /calendar — extend HabitLogResponse and CalendarDay to surface status + reason so iOS/web can render skipped days and reasons; DELETE /api/v1/habits/{habit_id}/log/{log_date} already removes any same-day row (works for un-skipping)

**Dependencies:**

- Slice 03 (iOS Today + HabitDetail online + Create/Edit wired to backend) — the Skip affordance and creation fields attach to screens that slice 03 first connects to the real API; slice 00 owns the mock versions
- Slice 04 (backend RRULE-aware streaks) — the streak_service must learn that status='skipped' is an explicit break with a reason; doing this independently would double the streak rewrite, so sequence after/with 04
- Alembic migration tooling (existing, `uv run alembic revision --autogenerate`) and pytest backend test infra (slice 01+ populates tests)
- No new third-party libraries; no Redis/Live Activity/widget dependency for v1

**Effort:** M · **Success metric:** Skip-intent reversal rate: of all Skip taps that surface the excuse-trap interstitial, the % where the user chooses 'Do it anyway' (or dismisses without skipping) instead of 'Skip anyway'. This is directly measurable from the new status='skipped' rows vs. completions logged within the trap flow (instrument an `outcome` on the skip/log calls or diff the resulting habit_logs status). Target: ≥25% of triggered skip intents are reversed into completions within the first 4 weeks of dogfooding. Secondary guardrail: completion rate on habits that have a non-null anticipated_excuse vs. those without, over a matched window. · **Suggested slice:** New slice — slice-12-precommitment-excuse-trap. It does not fit any existing slice's Definition of Done: it spans backend (two `habits` columns + a `habit_logs.status` discriminator + a new /skip endpoint + streak-service skip semantics) and BOTH client surfaces (iOS introduces a Skip affordance that no current slice builds, plus the excuse-trap interstitial and two creation fields; web mirrors them). Depends on slice 03 (iOS online CRUD/toggle) and slice 04 (computed-streak rewrite). Recommended placement: after CHECKPOINT C (offline + RRULE green), parallelizable with slices 06–09 since it touches Today/Create/Detail rather than notifications/widget/Live Activity. Keep it a thin vertical slice per incremental-implementation: (1) backend migration + /skip endpoint + schema/streak changes with RED pytest first, (2) iOS create/edit fields + Skip affordance + SkipExcuseSheet, (3) web create fields + Skip dialog, (4) detail/heatmap skip rendering.

---

## #8 · Momentum Physics (XP as Velocity) — 6/10

_Each habit carries a momentum value with real inertia — completing accelerates it, missing applies drag — and you level up speed, not a point total, visualized as a moving needle._

**Problem:** A binary streak is brittle: one missed day resets it to zero, which reads as punishment and is a known driver of churn after a slip ("what-the-hell effect"). The current system makes this worse — `streak_service.py` walks consecutive calendar days, so a single gap drops `current_streak` to 0 with no middle ground. Users get a cliff, not a slope. There is no representation of "you were on a roll and lost a little ground" versus "you've fully fallen off," so a 40-day-strong user who misses once feels identical to a brand-new user. Competitor XP bars don't solve this either: they only ever go up (a static cumulative point total), so they can't model decay and a miss simply means "no progress today," which is invisible and unmotivating.

**Solution:** Give each habit a `momentum` value (0–100 float) with simple physics, computed on-the-fly from `habit_logs` + the habit's RRULE — never stored as a points column, exactly mirroring the computed-streak architecture (single source of truth). Walk forward over the habit's *scheduled* dates (reusing slice-04's `schedule.expected_dates`/`is_scheduled` so weekday/MWF habits aren't penalized on off-days): each completed scheduled occurrence adds an acceleration impulse, each missed scheduled occurrence applies multiplicative drag, with diminishing returns near the 100 ceiling so momentum behaves like velocity with inertia rather than a counter. A miss is a deceleration (e.g. momentum 82 to 68), not a reset to 0. Derive a "speed level" (integer tier from the float, e.g. Idle/Building/Cruising/Flying) and `momentum_delta` (change since the previous scheduled occurrence) so the UI can show direction. Surface three new read-only fields on the existing `HabitResponse`: `momentum: float`, `momentum_level: int`, `momentum_delta: float`. The signature visual is a SwiftUI speedometer-style needle on the iOS habit detail (and a compact gauge on Today / web HabitCard) that animates from old value to new on each toggle — accelerating up when you complete, easing down when a miss is registered. The algorithm lives in a new pure `momentum_service.py` (`momentum_from_dates(scheduled_completed, scheduled_missed, ...) -> MomentumState`), unit-tested directly like the streak helpers; no migration, no new table, no scheduled job. Tunable constants (impulse, drag factor, half-life) live in one config block so the curve is adjustable without touching call sites.

**User story:** As a habit tracker who missed yesterday after a strong 3-week run, I want my habit to show a slight slowdown of its momentum needle instead of resetting to zero, so that one slip feels like losing a little speed I can quickly regain rather than throwing away all my progress — and I come back today instead of abandoning the habit.

**Surfaces:**

- Backend: new app/services/momentum_service.py (pure algorithm + async wrapper) consuming app/services/schedule.py (slice-04) and the same habit_logs query as streak_service.py
- Backend: app/services/habit_service.py list_habits()/get_analytics() and app/routers/habits.py get_habit()/update_habit()/create_habit() populate the 3 new HabitResponse fields
- Backend: app/schemas/habit.py — add momentum, momentum_level, momentum_delta to HabitResponse (and optionally to HabitAnalytics)
- iOS: Features/HabitDetail — new MomentumGauge.swift (SwiftUI Canvas/Shape animated needle) as the hero element above the existing heatmap/WeeklyChart
- iOS: Features/Today/HabitRow.swift — compact momentum mini-gauge + level glyph; animate on optimistic toggle in TodayViewModel
- iOS: Core/Networking/DTO+Habits.swift — add the 3 fields to HabitDTO; Core/Theme — gauge styling for both Liquid Glass and Health Cards themes
- Web: frontend/src/types/habit.ts (extend Habit), frontend/src/components/habits/HabitCard.tsx + habits/[id] detail — small SVG/Recharts radial gauge
- Onboarding/empty-state copy: one-line explainer of momentum so the needle isn't mysterious on first use

**Data model:** No schema change and no migration — momentum is a derived float computed from existing habit_logs.completed_date plus habits.rrule and habits.created_at (anchor), identical sourcing to computed streaks (single source of truth, consistent with the no-streaks-table decision in CLAUDE.md). Only the API response contract grows: HabitResponse (Pydantic, backend/app/schemas/habit.py) and the matching web Habit interface (frontend/src/types/habit.ts) and iOS HabitDTO gain three read-only fields — momentum: float (0–100), momentum_level: int (e.g. 0–4), momentum_delta: float (signed change vs previous scheduled occurrence). A small internal MomentumState dataclass/struct (value, level, delta) is the service return type. Tunable constants (acceleration impulse, drag multiplier, ceiling soft-cap / half-life) are module-level config, not DB rows. If profiling later shows repeated recomputation is hot, cache the float per habit in Redis DB#2 with short TTL (same escape hatch the architecture already names for streaks) — not required for v1.

**Endpoints:**

- No new routes. GET /api/v1/habits (list) — each item now includes momentum, momentum_level, momentum_delta
- GET /api/v1/habits/{habit_id} — includes the 3 momentum fields (primary fuel for the detail-screen needle)
- POST /api/v1/habits/{habit_id}/log and DELETE /api/v1/habits/{habit_id}/log/{log_date} — unchanged contract, but the next habit fetch reflects the new momentum so the gauge animates after a toggle
- GET /api/v1/habits/{habit_id}/analytics — optionally surface momentum + momentum_level alongside existing streak fields (additive, behind same handler)
- POST /api/v1/habits (create) and PUT /api/v1/habits/{habit_id} (update) — response includes momentum (0.0 for a brand-new habit)

**Dependencies:**

- Slice-04 (Backend RRULE-aware streaks) — HARD dependency: momentum_service reuses app/services/schedule.py (expected_dates / is_scheduled / previous_scheduled_date) so off-days don't count as misses. Building momentum on the current naive day-by-day basis would re-introduce the weekend-penalty bug. If slice-04 is unshipped, sequence it first.
- Slice-03 (iOS Today + HabitDetail wired online) — needed so there is a real detail screen + HabitDTO + optimistic-toggle path to attach the animated gauge to.
- Slice-00 theme system (AppTheme protocol, Liquid Glass / Health Cards) — gauge must render in both themes.
- Existing: dateutil.rrule (Python, already a dependency); SwiftUI Canvas/Animatable + Swift Charts (iOS); Recharts/SVG (web, already in stack). No new third-party packages required.

**Effort:** M · **Success metric:** Primary (retention after a slip): among users who miss at least one scheduled day after a 7+ day active run, 14-day return rate improves by >=15% relative to the pre-momentum cohort (the binary-reset baseline) — measured via the slice-10 admin metrics / logs-per-day pipeline by comparing post-miss re-engagement before vs after launch. Guardrail/correctness: momentum_service unit tests prove a single miss on a strong habit decreases momentum by a bounded amount and never resets to 0 (e.g. >=50% of prior value retained after one miss), daily-habit and weekday/MWF habits behave per RRULE, and the field adds <10ms p95 to GET /habits/{id} (it reuses the same single indexed habit_logs range scan as streaks, so no extra query). · **Suggested slice:** Attaches primarily to slice-04 (Backend RRULE-aware streaks) for the computation half — momentum_service.py is the architectural twin of streak_service.py and shares schedule.py — then needs a small NEW presentation slice (propose slice-12 "iOS + Web Momentum Gauge") for the animated needle UI, since slices 00–11 contain no gamification/visualization surface and slice-03's detail screen is already defined as streak+heatmap+chart only. Concretely: add momentum_service + the 3 response fields + tests as an additive task block within slice-04 (no migration, low risk), and create slice-12 for MomentumGauge.swift (iOS detail hero + Today mini-gauge) and the web HabitCard/detail gauge. The new slice slots after slice-05 (so offline cache can carry the derived value) and can run in parallel with notifications/widget slices 06–08.

---

## #9 · Earned Streak Freezes (Loss-Aversion Insurance) — 5.67/10

_Earn a small capped stash of freeze tokens through real over-delivery (1 per 7 perfect days, max 3), RRULE-aware so a weekday habit can't be frozen on a Saturday it was never due._

**Problem:** Streaks today are all-or-nothing: one missed scheduled day resets `current_streak` to 0. The live algorithm in `backend/app/services/streak_service.py` (`current_streak_from_dates`) breaks the moment a scheduled day has no `habit_logs` row. For a primary user (Armando) and TestFlight family who log via iOS in under 3 seconds, a single sick day or travel day vaporizes a 60-day streak — the exact loss-aversion that motivates the streak also makes it brittle and demoralizing, which is the #1 driver of habit-tracker churn. We want to soften the cliff WITHOUT removing the loss-aversion stakes (free unlimited skips would kill the mechanic). The honest framing: freezes must be EARNED through real over-delivery, capped so they can't be farmed, and RRULE-aware so a weekday-only habit can't waste a freeze on a Saturday it was never due.

**Solution:** Add an earned, capped, schedule-aware "streak freeze" that bridges a single missed scheduled occurrence so the consecutive-day count survives. Earning rule: a habit accrues 1 freeze token per 7 consecutive PERFECT scheduled completions (no gaps, no prior freeze used in that run), capped at MAX_FREEZES=3 per habit; tokens never expire but stop accruing at the cap. Spending rule: when the streak walk-back (which after slice-04 steps through SCHEDULED dates via `schedule.previous_scheduled_date`) hits exactly ONE missed scheduled date AND a token is available, the algorithm consumes one token, records a `habit_freeze` row for that date, and continues the streak instead of stopping. A gap of 2+ consecutive missed scheduled dates is never auto-bridged (one token covers one occurrence). Freezes are applied lazily at read time during streak computation (consistent with the project's computed-not-stored decision in CLAUDE.md), then the consumption is persisted to `habit_freezes` so the same day isn't re-charged and so balance is auditable. RRULE-awareness is inherited for free from slice-04's `schedule.is_scheduled` — only scheduled dates count toward the 7-perfect-day earn and only a missed *scheduled* date can be frozen; off-days (e.g. weekends for a weekday habit) are skipped entirely and cost nothing. The feature is OFF by default per habit (`freeze_enabled` flag) so existing streak semantics are unchanged until the user opts in, keeping slice-04's behavior the baseline and making this an additive, reversible layer.

**User story:** As Armando logging habits daily on iOS, when I miss a single scheduled day on a habit I've been perfect at for weeks, I want a previously-earned freeze to automatically bridge that one day so my streak survives — and I want to see how many freezes I have left and that they were earned by my own consistency — so that one bad day doesn't erase weeks of progress and demotivate me, while still feeling like the streak is real and not free.

**Surfaces:**

- Backend: app/services/streak_service.py (freeze-aware streak walk; new pure helper compute_streak_with_freezes consuming schedule.is_scheduled/previous_scheduled_date from slice-04)
- Backend: app/services/freeze_service.py (NEW — accrual calculation, balance, idempotent consumption)
- Backend: app/models/habit.py (add freeze_enabled column) + app/models/habit_freeze.py (NEW model)
- Backend: app/schemas/habit.py (HabitResponse gains freezes_available, freezes_used_total, freeze_enabled; HabitCreate/HabitUpdate gain freeze_enabled)
- Backend: app/routers/habits.py (surface freeze fields in existing GET endpoints; add GET /{id}/freezes ledger)
- Backend: alembic/versions (NEW migration: habits.freeze_enabled + habit_freezes table + composite index)
- Web: frontend HabitCard / habit detail page (freeze-shield badge + 'N freezes left' pill; frozen days rendered distinctly on StreakCalendar heatmap)
- Web: CreateHabitModal / edit form (freeze_enabled toggle)
- iOS: HabitResponse decode + PersistedHabit @Model mirror (freezesAvailable, freezeEnabled) so widget/Live Activity reflect frozen streaks via App Group SwiftData
- iOS: Today/HabitDetail views (shield glyph + frozen-day styling in heatmap, both Liquid Glass + Health Cards themes)
- iOS: Settings/edit habit (freeze_enabled toggle, localized ES/EN)

**Data model:** New table habit_freezes: id UUID PK (UUIDMixin), habit_id UUID FK->habits(id) ON DELETE CASCADE NOT NULL indexed, frozen_date DATE NOT NULL (the scheduled occurrence the token covered), created_at/updated_at (TimestampMixin), UNIQUE(habit_id, frozen_date) to make consumption idempotent and prevent double-charging a day. Composite index (habit_id, frozen_date DESC) to align with the streak walk-back range scan added in slice-04. Alter habits: add freeze_enabled BOOLEAN NOT NULL DEFAULT false. Token balance is NOT stored as a counter — it is DERIVED: available = min(MAX_FREEZES, floor(perfect_scheduled_run_segments / 7)) − count(habit_freezes for this habit), computed from habit_logs + habit_freezes + the habit's rrule, preserving the project's single-source-of-truth / computed-streaks architectural decision. No streaks table is introduced (consistent with existing design). Constants MAX_FREEZES=3 and EARN_EVERY=7 live in app/core/config.py (Pydantic Settings) so they are tunable without a migration.

**Endpoints:**

- GET /api/v1/habits — HabitResponse[] now includes freezes_available, freezes_used_total, freeze_enabled (no new route; additive fields)
- GET /api/v1/habits/{habit_id} — same additive fields on detail HabitResponse
- POST /api/v1/habits and PUT /api/v1/habits/{habit_id} — accept freeze_enabled in HabitCreate/HabitUpdate
- GET /api/v1/habits/{habit_id}/freezes — NEW: returns the freeze ledger (list of {frozen_date, created_at}) plus {available, used_total, earn_progress_days, next_earn_in_days} for UI; auth-gated and ownership-checked like every other habit route via get_current_user + habit_service.get_habit
- GET /api/v1/habits/{habit_id}/calendar — CalendarDay gains optional frozen: bool so heatmaps can render frozen days distinctly (additive)

**Dependencies:**

- HARD: Slice-04 (RRULE-aware streaks) MUST land first — it creates app/services/schedule.py (is_scheduled, previous_scheduled_date) and rewrites streak_service.py to walk SCHEDULED dates. Today schemas/habit.py rejects any non-daily rrule (normalize_daily_rrule), so the 'RRULE-aware' promise is impossible until slice-04 ships multi-rule support and the composite indexes on habit_logs(habit_id, completed_date).
- HARD: Slice-03 (iOS online Today/HabitDetail) for a real client showing freeze UI; Slice-05 (SwiftData mirror + App Group) so widget (07) and Live Activity (08) reflect frozen streaks.
- SOFT: Slice-04's ADR pattern (docs/adr/000x) — this change alters streak semantics again, so it needs its own ADR documenting earn/spend rules and rollback (drop habit_freezes + freeze_enabled).
- SOFT: dateutil.rrule already in backend deps (used by slice-04) — no new Python dependency. No new npm or SwiftPM dependency.
- DECISION GATE: confirm earn=1/7 perfect days, cap=3, single-occurrence bridge only, opt-in per habit default OFF — these are tunable but must be locked before build.

**Effort:** M · **Success metric:** Streak-survival rate: percentage of streaks ≥14 days that survive their first single missed scheduled day rises from 0% (today every miss resets) to ≥80% among freeze_enabled habits, measured over a 30-day dogfood window on the TestFlight cohort via the admin metrics surface (slice-10). Guardrail metric: no streak should ever survive a 2+ consecutive-scheduled-day gap (auto-bridge is strictly single-occurrence) — verified by 0 occurrences in the habit_freezes ledger where two adjacent scheduled dates are both frozen within one streak run. Correctness gate: parametrized pytest matrix over (rrule × log-pattern × token-balance) is 100% GREEN, including 'weekday habit, missed one Wednesday, 1 token earned → streak intact and token decremented' and 'no token available → legacy reset behavior preserved'. · **Suggested slice:** Attach to an existing slice — make it a follow-on inside Slice-04's lane, not a new top-level slice. Recommended sequencing: keep Slice-04 (RRULE-aware streaks + composite indexes) exactly as planned, then add this as 'Slice-04b' tasks immediately after Task 4.3, reusing the same schedule.py helpers, the same regression-snapshot discipline (deprecation-and-migration), and the same ADR folder. Rationale from the dependency graph in plans/000-OVERVIEW.md: this feature is a pure backend streak-semantics extension that only becomes correct once 4.3 makes streaks schedule-aware; bolting it onto Slice-04 avoids a second round of regression snapshots and a second composite-index migration. The thin iOS/web presentation layer (shield badge + freeze toggle + frozen-day heatmap styling) rides along in Slice-03/05 (iOS) and the web HabitCard work as additive fields on the already-shared HabitResponse — no new client slice required.

---

## #10 · Interactive Home & Lock Screen Widgets (with "Quick 3" at-risk variant) — 5.67/10

_A widget family where each habit circle is a real App-Intents button — tap to complete in place with optimistic fill — including a 'Quick 3' variant showing only your most-at-risk streaks._

**Problem:** The north-star is logging a habit in under 3 seconds, but today every completion requires unlocking, finding the app, opening it, and tapping a row. Slice-07 ships a widget, but its current spec treats tap-to-log as a single AppIntent on a Small/Medium grid without guaranteeing the circle visually fills *before* the timeline reloads — so the user sees a lag/flicker that breaks the sub-3-second feel. Worse, no surface answers the only question that matters at a glance: "which of my streaks am I about to lose today?" A user with 8 habits sees an undifferentiated grid and still has to think. The Home Screen should be the app, and the widget should be a triage surface, not a launcher.

**Solution:** Upgrade the slice-07 widget into a fully interactive widget *family* on iOS 26 where each habit circle is a real `Button(intent:)` backed by App Intents — tapping it completes the habit in place with an immediate optimistic fill (the circle animates filled in the same timeline render, before any network round-trip), enqueued through the existing offline WriteQueue so it syncs like any other write. Add a new "Quick 3" variant (systemMedium + accessoryRectangular) that shows only the 3 habits whose streaks are most at risk today — scheduled-for-today, not-yet-completed, ranked by an at-risk score (longer current streak + closer to the user's reminder time/midnight = higher priority). The at-risk ranking is computed by a shared scoring function: client-side via the slice-05 StreakComputer so the widget works offline, and mirrored server-side in streak_service so the web dashboard and any future server-driven timeline agree. Optimistic-fill correctness: the AppIntent writes the optimistic log into the App Group SwiftData store synchronously inside perform(), then returns, so WidgetKit's automatic post-intent reload already reads the filled state; a rollback path un-fills if the queued write later hard-fails (e.g. 4xx). Lock Screen accessoryCircular shows "done/total" with a gauge; accessoryRectangular shows the single most-at-risk habit as a tappable line.

**User story:** As Armando glancing at my Home Screen between meetings, I want to tap a habit's circle directly on the widget and see it fill instantly, and I want a "Quick 3" widget that shows me only the streaks I'm about to lose today, so that I can protect my streaks in under 3 seconds without ever opening the app.

**Surfaces:**

- iOS WidgetKit extension — HabitTrackerWidget (extends slice-07): new interactive Button(intent:) circles with optimistic fill on systemSmall/systemMedium
- iOS WidgetKit — new 'Quick 3' widget kind (systemMedium + accessoryRectangular + accessoryCircular lock-screen) showing most-at-risk streaks
- iOS App Intents — LogHabitIntent upgraded for synchronous optimistic write + new rollback handling; widget-scoped intent target
- iOS Core/Services — StreakComputer extended with atRiskScore(habit, logs, now) used by both widget variants offline
- iOS Core/Persistence — SharedStoreReader gains todayAtRisk(limit:) returning ranked WidgetHabit list from the App Group store
- Backend FastAPI — new GET /api/v1/habits/today aggregate returning per-habit completed_today + current_streak + at_risk_score (web parity, single source of ranking)
- Backend services/streak_service.py — at_risk_score() helper mirroring the Swift ranking
- Web Next.js (optional parity) — a 'Quick 3 / At-risk today' card on the dashboard reusing the new /today endpoint

**Data model:** No required schema change — at-risk ranking is computed from existing columns (habits.rrule, habits.reminder_time [added in slice-06], habit_logs.completed_date) plus the already-computed current_streak. The widget reads the slice-05/07 App Group SwiftData store (PersistedHabit, PersistedHabitLog, WriteOp); no new @Model types are strictly needed, though WidgetHabit (slice-07 display model) gains two derived fields: atRiskScore: Double and isScheduledToday: Bool (computed, not persisted). OPTIONAL additive enhancement: habits.protect_streak BOOLEAN NOT NULL DEFAULT true — lets a user opt a habit out of the at-risk surface (e.g. 'nice to have' habits never appear in Quick 3); if added, mirror as PersistedHabit.protectStreak and include in HabitResponse. Recommend shipping without it first and adding only if triage feels noisy.

**Endpoints:**

- GET /api/v1/habits/today — NEW aggregate: returns [{id, name, color, rrule, scheduled_today: bool, completed_today: bool, current_streak: int, longest_streak: int, reminder_time: time|null, at_risk_score: float}] for the authed user; powers web 'Quick 3' parity and pins the canonical ranking. Auth required; excludes archived.
- GET /api/v1/habits/today?at_risk=3 — optional query to return only the top-N at-risk, not-yet-completed, scheduled-today habits (server-side sort), so web and any future server-driven widget timeline match the client ranking exactly.
- POST /api/v1/habits/{habit_id}/log — EXISTING (reused unchanged): the AppIntent's WriteQueue op flushes through this; returns 201 or 409 on duplicate-per-date (idempotent-friendly, treat 409 as success for optimistic reconcile).
- DELETE /api/v1/habits/{habit_id}/log/{log_date} — EXISTING (reused): backs the un-fill/rollback path if a user toggles a circle off from the widget.

**Dependencies:**

- Slice-07 (iOS Home/Lock widget, App Group SwiftData store, WidgetTheme, base LogHabitIntent) — this feature EXTENDS it; do not build standalone
- Slice-05 (SwiftData App Group container, WriteQueue, SyncEngine, StreakComputer) — interactive optimistic write and offline at-risk scoring depend on it
- Slice-06 (habits.reminder_time column + PersistedHabit.reminderTime) — needed for time-proximity term in at_risk_score; degrade gracefully to midnight if a habit has no reminder
- Slice-04 (RRULE-aware streaks + schedule.py) — 'scheduled today' and streak-at-risk both need is_scheduled(rrule, today); StreakComputer is the Swift port of this
- iOS 26 WidgetKit interactive widgets (Button(intent:)/Toggle(intent:)) and App Intents — platform baseline, already targeted by SPEC
- Apple App Group entitlement group.com.armandointeligencia.HabitTracker — provisioned in slice-05/07

**Effort:** M · **Success metric:** Time-to-log a habit from the Home Screen widget (widget tap to optimistic fill visible) is ≤1s with no app launch, measured in simulator/device; and ≥70% of widget completions over a TestFlight week originate from the 'Quick 3' / interactive circles rather than opening the app (instrument via a lightweight WriteOp.source field: .widgetQuick3 / .widgetGrid / .app). Secondary: at-risk ranking precision — of habits shown in Quick 3 that the user does NOT complete that day, the streak actually broke (i.e. the surface flagged real risk), spot-checked against logs. · **Suggested slice:** Attaches to slice-07 (iOS Home Screen / Lock Screen widget) as an enhancement — recommend a 'slice-07b' or expanded slice-07 Tasks 7.6–7.8 rather than a brand-new top-level slice, since target scaffolding, SharedStoreReader, WidgetTheme, and the base LogHabitIntent already exist there. New work concentrated in: (1) upgrading LogHabitIntent to synchronous optimistic write + rollback, (2) StreakComputer.atRiskScore + SharedStoreReader.todayAtRisk, (3) the new 'Quick 3' widget kind + views, and (4) the thin backend GET /api/v1/habits/today aggregate (the only cross-surface/web-parity piece, which could alternatively fold into slice-10 web-admin if web parity is deferred).

---


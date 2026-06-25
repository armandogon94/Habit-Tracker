# Habit Tracker — Executive Summary of the Opus Analysis Fleet

> Generated 2026-06-25 by a **throttled fleet of Opus workflows**. ~14M subagent tokens across 4 completed workflows. Companion deep-dives: [`01-adversarial-code-review.md`](01-adversarial-code-review.md), [`02-five-angle-analysis.md`](02-five-angle-analysis.md), [`03-feature-brainstorm.md`](03-feature-brainstorm.md), [`04-spec-plan-redteam-partial.md`](04-spec-plan-redteam-partial.md).

## What ran

| Workflow | Result | Tokens | Report |
|---|---|---|---|
| Adversarial code review | ✅ 62 confirmed findings (77 raw, 15 refuted by skeptics) | ~4.9M | 01 |
| Five-angle analysis | ✅ 5 expert angles + chief-strategist synthesis | ~0.9M | 02 |
| Feature brainstorm | ✅ 110 ideas → 30 ranked → top-10 mini-specced | ~6.6M | 03 |
| Spec/plan red-team | ⚠️ **Partial** — 4 of 14 docs (hit session limit) | ~1.1M | 04 |
| Competitive research | ❌ Not run (session limit) | — | — |

**A note on method:** the first attempt fired all 5 workflows at once (~40 concurrent Opus agents) and tripped a server-side 429 burst-throttle. Re-running them **one at a time** (≤8 concurrent) fixed it — until the red-team, which hit the harder **Claude session limit (resets 10:50pm America/New_York)**. Two items remain; see "What's left."

---

## 🔴 Fix today — the one ship-blocker

**Hardcoded JWT signing secret → full account takeover.** `JWT_SECRET` defaults to a repo-committed string in [`backend/app/core/config.py:6`](../backend/app/core/config.py) with no startup guard, and HS256 is symmetric. A verifier reproduced it at runtime: `Settings().JWT_SECRET == 'dev-secret-…'`. Anyone with the repo can mint a valid token for any `sub` and take over any account, including the planned admin routes — this collapses the entire per-user ownership model. Three separate review agents flagged it independently.

**Fix:** remove the default, add a fail-closed validator (reject empty / <32 chars / `dev-secret*`), inject via secret manager, **rotate the exposed key.** Same pattern applies to the DB password (real hardcoded copy lives in [`alembic.ini:3`](../backend/alembic.ini), per the red-team — *not* `config.py` as slice-01 assumed).

---

## The three findings every workflow converged on

### 1. The risk is **sequencing & contract drift**, not capability
- The codebase is a genuine stub: iOS is 5 files (`RootView` = "Scaffold ready", 47 lines), the backend is 2 routers; the repositories/analytics/admin layers named in `CLAUDE.md` are **fictional**.
- The red-team found **all four critiqued slice plans were written against an imagined codebase**: slice-04 is built for weekday/weekly RRULEs but the backend hard-rejects everything except `FREQ=DAILY` ("fatal, plan-invalidating"); slice-03's documented endpoints/DTO fields don't match `routers/habits.py`; slice-01's "remove hardcoded password" targets the wrong file; slice-00 treats an already-executed scaffold as greenfield.
- **Implication:** the data-identity, security, correctness, and design *contracts* are about to be frozen by slices 03–08. Fixing them now costs hours; after those slices land it costs weeks.

### 2. The product is investing in **polish over retention**
- Five-angle scored Product Strategy **4/10** (everything else 5.5): *"a technically excellent build of a product that has opted out of being a product."* It ships **zero retention loops** beyond a disableable reminder, while spending its richest budget on Live Activities / widgets / dual themes.
- The brainstorm's 3-judge panel **independently confirmed this**: the top 8 features are all cheap, research-backed *behavioral mechanics*; the SPEC's headline native features ranked mid/low (Interactive Widgets 5.67, Live Activity 4.67, HealthKit 4.67, Streak Pacts 4.67, Siri 3.67).

### 3. The build is **over-scoped for its audience**
- SPEC §1 defines the entire user base as "Armando + family/friends + admin (also Armando)" — n≈1–10 — yet commits ~12 slices across three surfaces (native iOS, web admin, backend) including a full admin metrics app to administer a handful of accounts.
- **Either** add the one mechanic that turns n=1 into a retention/referral loop (shared "Habit Pacts" among the family already on TestFlight) **or** admit it's a personal tool and cut the web-admin slice. Right now it has the cost structure of a commercial app and the reach of a hobby project.

---

## Prioritized action plan (deduplicated across all four workflows)

### 🔴 NOW — Foundation + security floor (hours; before *any* new slice)
1. **Secrets:** mandatory `JWT_SECRET` with fail-closed validator + `SecretStr`; strip plaintext DB password from `alembic.ini`; make Alembic read `DATABASE_URL` (it currently ignores it and always hits localhost).
2. **Auth floor:** rate-limit `/auth/*` (slowapi isn't even a dependency yet); rotate refresh tokens; implement the Redis whitelist that the docs *claim* exists so logout/suspend actually revoke. Require `exp` on JWT decode (forged tokens currently never expire).
3. **Log contract:** add `client_log_id` + idempotent **200-on-replay** to `POST /log` *now* — the entire offline-sync model (slice-05) depends on this contract, and `log_completion` currently 500s on duplicate taps instead of 409.
4. **Global exception handler** (the promised `core/exceptions.py` doesn't exist) so uncaught errors stop leaking as 500s/stack traces.

### 🟠 NEXT — Reconcile the plan with reality + force the fork
5. **Rewrite slices 01/03/04 against ground truth** before executing them (they reference endpoints, DTOs, and RRULE support that don't exist). Re-run the red-team on the corrected plans.
6. **Fix the two core-correctness bugs that break the product's promise:** streaks ignore the RRULE (non-daily habits break on every skipped day) and `users.timezone` is stored but never used (server-UTC boundaries + the *frontend logs against the UTC date*, so any non-UTC user logs the wrong day). These are the heart of slice-04 and must be made schedule- and timezone-aware.
7. **Force the personal-tool-vs-product fork** in writing at the top of `SPEC.md`. It gates everything below.

### 🟡 THEN — Build the retention layer (cheap behavioral mechanics, top of the brainstorm)
8. **Temptation Bundling Pairs (7.0/10, effort M)** — pair a "want" with a "should"; reframe reminders nag→invitation; track drag-along rate. Purely additive schema, no competitor ships it.
9. **Anchor Builder (6.83)** — structured implementation-intention composer ("After I ☐, I will ☐ at ☐").
10. **Never-Miss-Twice Guardrail (6.67)** — detect one miss, escalate a recovery nudge before the streak dies (proposed `slice-12`).
11. **Grounded Weekly Reflection (6.67, AI)** + **Comeback Mode (6.5)** + **Prestige/Graduate-a-Habit (6.33)**.
12. **Collapse the Today read path** to one `O(streak)` query + a `(habit_id, completed_date DESC)` index + write-through Redis cache — fixes the N+1 explosion *before* widgets/Live-Activity/offline-pull all hammer it.

### ⚪ LATER — Native polish (the SPEC's current focus; lower ROI per the judges)
Widgets, Live Activity, HealthKit, Siri/App Intents. Genuinely nice, but they ranked mid-pack — sequence them after the retention layer, not before.

---

## Tensions you must resolve (decisions you owe)

| Decision | The conflict | Recommendation |
|---|---|---|
| **Personal tool vs. product** | Drives whether to cut web-admin or add a social loop | Pick explicitly in SPEC §1 before slice 03 |
| **Social Pacts vs. privacy** | Shared check-ins make this GDPR Art. 9-adjacent *health* data with no consent/export/deletion path | If "product": add account-deletion + data-export as a slice; if "personal": skip social |
| **Redis savior vs. SPOF** | Wanted for streak cache *and* token whitelist, but becomes a single point that could mass-logout everyone | Degrade gracefully (cache miss → recompute; whitelist outage → fail-open read, fail-closed write) |
| **Engagement richness vs. battery** | Per-minute Live Activity tick + widget refresh fight the single-query/battery mandate | Hourly widget refresh + relevance-based; Live Activity ticks client-side, not via push |

---

## What's left + how to resume

Blocked by the session limit (resets **10:50pm America/New_York**):
- **Finish the red-team** — 10 remaining docs (SPEC, overview, slices 02, 05–11) + the cross-doc synthesis (missing slices, resequencing).
- **Competitive & market research** — never ran; needs a fresh attempt (and a check that web-search tools resolve inside workflow agents).

Both are saved, known-good scripts. After reset, re-run:
```
Workflow({ scriptPath: ".../habit-spec-plan-redteam-wf_bb028073-8f4.js" })   # finish red-team
Workflow({ scriptPath: ".../habit-competitive-research-wf_8a2c7e78-d6a.js" }) # competitive
```
(One at a time — the throttle is what kept the big runs alive.)

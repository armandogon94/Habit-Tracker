# Slice 01 — Auth Hardening Review

> Redis-backed refresh-token rotation/revocation + auth rate limiting. Verified by
> two Opus workflows: a pre-implementation **design-pitfall** pass (4 lenses +
> synthesis, ~486K tokens) and a post-implementation **adversarial review** (5
> dimensions × skeptic verification, ~1.67M tokens, 20/26 findings confirmed).
> 117 backend + 7 frontend tests pass; ruff + tsc clean.

## What shipped

| Area | Behavior |
|---|---|
| Whitelist | Every refresh token carries a `jti`; only whitelisted jtis are honored (`refresh:{jti}` → user_id, TTL = refresh lifetime; `refresh_user:{user_id}` set index). |
| Rotation | `/refresh` **atomically** consumes the presented jti (`GETDEL`) and issues a fresh whitelisted one — concurrent refreshes of the same jti can never both win. |
| Reuse detection | A well-formed but already-consumed jti → 401 **and revokes every session** for the user (RFC 6819). |
| Revocation | `/logout` deletes the jti server-side (and cleans the user index). |
| Rate limiting | slowapi 10/min by **socket-peer IP** on login/register/refresh → 429. |
| Fail-closed | A Redis outage on an auth path returns a deliberate **503**, never 500/fail-open. |
| Client | `apiFetch` coalesces concurrent 401s into a single `/refresh` (single-flight) so a benign stampede can't trip reuse detection. |

## Findings fixed (with tests)

- **TOCTOU race in rotation (HIGH ×2, both workflows' #1).** The original `is_valid()` … `revoke()` was check-then-act across two awaits (incl. a DB round-trip); two concurrent refreshes could both pass and **fork the session**. Replaced with atomic `GETDEL` consume. Proved by `test_consume_is_atomic_only_first_wins` and the HTTP-level `test_concurrent_refresh_only_one_wins`.
- **Rate-limit IP spoofing (HIGH).** `client_ip` trusted `X-Forwarded-For` unconditionally → any client spoofs it for a fresh bucket, nullifying brute-force protection. Now uses the socket peer only; proxy trust is pushed to the boundary (uvicorn `--proxy-headers --forwarded-allow-ips`).
- **Force-logout DoS via jti-less token (LOW).** A legacy/forged refresh token with no `jti` used to trigger `revoke_all`. Now rejected 401 without revoking; only a consumed jti triggers family revocation. (`test_refresh_with_no_jti_is_401_without_revoking_all`)
- **Undifferentiated Redis-down 500 → deliberate 503** (`test_refresh_returns_503_when_redis_unavailable`).
- **logout left a dangling index member** — now passes `user_id` to `revoke`.
- **Zero real-endpoint rate-limit / e2e coverage (HIGH).** Added `test_real_login_endpoint_is_rate_limited` and `test_login_issues_whitelisted_jti_and_cookie_drives_refresh`, plus no-cookie 401.

## Deliberately deferred (documented per the design synthesis)

These are conscious v1 choices, not oversights — each is safe as-is and tracked for a later slice:

1. **Session-family (`sid`) scoped revocation.** v1 revokes **all** of a user's sessions on any reuse event (conservative/secure). A per-login `sid` would scope revocation to one device — nicer UX, deferred. The jti-less-token guard already removes the worst DoS.
2. **Absolute family-expiry cap (`fexp`).** v1 uses **sliding** refresh (each rotation re-issues a 7-day token). Bounding total session age to `min(7d, fexp-now)` is a hardening follow-up.
3. **Redis-backed rate-limit storage.** Limiter storage is in-process per worker; behind a multi-worker/multi-replica deployment the effective limit multiplies. Switch to `storage_uri=settings.REDIS_URL` (fail-open) when scaling out.
4. **`Retry-After` on 429.** slowapi's `headers_enabled` fights FastAPI's `response` injection; the plain 429 is shipped, header is a follow-up.
5. **Production proxy config.** No `docker-compose.prod.yml` exists yet; when it lands it must run uvicorn with `--proxy-headers` and `--forwarded-allow-ips=<Traefik subnet>` (never `*`) so `client_ip` resolves the real client.
6. **User-index pruning** of organically-expired members + a max-sessions-per-user cap (minor housekeeping).
7. **Per-endpoint rate tuning** (tighter register, looser refresh) — revisit when the mobile client lands.

## Remaining (the full Slice 01 plan)

Mobile JSON auth endpoints (`/auth/*-mobile`) and the `users.role` enum/admin gating are still pending — they serve the not-yet-built iOS app and the web-admin slice, and reuse the same rotation/consume service implemented here.

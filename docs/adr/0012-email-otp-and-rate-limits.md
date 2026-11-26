# 0012 — Email OTP as an opt-in second factor; fixed-window rate limits

**Context.** The brief asks for 2FA with a code sent by email and for rate limiting. We had
to decide when 2FA applies, how codes are stored and attempted, and how to limit abuse of
the auth endpoints.

**Decision — 2FA.**
- **Opt-in per user** (`users.is_2fa_enabled`), only after the email is verified, and
  toggling it requires the password again (a stolen access token can't switch it off).
- Login with 2FA returns `{"status": "otp_required", "challenge_id", "expires_in"}` instead
  of tokens (a discriminated union on `status`); `POST /auth/2fa/verify` finishes the login.
- The **challenge** lives in Redis for 10 min: `{uid, code, attempts, sends}`. The worker
  generates the 6-digit code (`secrets.randbelow`) when it sends the email, like ADR-0011.
- The code is stored as **HMAC-SHA256 with the server secret**: 10^6 codes would be
  brute-forced from a plain hash in milliseconds; compared with `hmac.compare_digest`.
- **5 wrong codes → the challenge is deleted and the user is locked for 15 min** (`429
  otp_locked` with `Retry-After`). A resend replaces the code but keeps the attempt counter,
  and there are at most 3 sends per challenge.

**Decision — rate limits.** Fixed window in Redis (`INCR` + `EXPIRE NX`, one pipeline):
- per IP on every auth endpoint (login 10/min, register 5/10 min, emails 5/15 min, ...);
- per account on login (20 per 15 min, key = hash of the email), which stops slow guessing
  of one password from many IPs;
- `429 rate_limited` with `Retry-After`; `RATE_LIMIT_ENABLED=false` switches it off.

**Alternatives.**
- *TOTP (authenticator app)*: stronger, works offline, but the brief asks for email codes and
  it needs QR enrolment and recovery codes; a natural "future work" item.
- *2FA for everyone*: more secure, but every demo login would need Mailpit.
- *Sliding window / token bucket*: smoother, but more state or a Lua script per request; the
  fixed window's 2x burst at a boundary doesn't matter for brute-force protection.

**Consequences.** Someone who knows the password can lock the owner out of logging in for
15 minutes — accepted, since they already hold the password and the owner gets the
emails. Behind a proxy, uvicorn must trust `X-Forwarded-For`, or all clients share one IP.

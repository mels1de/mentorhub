# 0010 — Auth implementation: users table, refresh-token families, request authentication

**Context.** ADR-0005 fixed the token model (15 min JWT access token, rotating opaque refresh
token in Redis). Implementing it in Phase 1 needed concrete choices about storage, reuse
detection, concurrency and how a request is authenticated.

**Decisions.**

1. **`users.role` is `VARCHAR(16)` + `CHECK`**, not a native Postgres `ENUM`. Adding a role
   is a constraint swap in a normal migration; `ALTER TYPE ... ADD VALUE` has transaction
   restrictions and values can never be removed. `email` is `citext UNIQUE`, so uniqueness
   and lookups are case-insensitive in the database, not in Python.
2. **Passwords: Argon2id via `pwdlib`** with its recommended parameters. On login
   `verify_and_update` re-hashes when the parameters change. For an unknown email we still
   verify against a dummy hash, so response time does not reveal which emails exist; the
   error is identical (`invalid_credentials`) for both cases.
3. **Refresh tokens are grouped into families** (one family = one login on one device):
   - `auth:rt:{sha256(token)}` → `{uid, fam, used, used_at}`; only the hash is stored.
   - `auth:fam:{id}` exists while the login is alive (sliding 7-day TTL).
   - `auth:user:{id}:fams` lists a user's families for "log out everywhere".
   Rotation marks the old token used instead of deleting it, which is what makes reuse
   detectable: a used token presented again revokes the whole family (OWASP / RFC 9700
   "refresh token rotation with reuse detection").
4. **Claim is one atomic Lua script** (`HINCRBY used`), so of N concurrent refreshes with
   the same token exactly one wins. Reuse **within 10 s** of the first use is answered with
   a plain 401 and *no* revocation — that is two tabs refreshing at once, not theft. The
   late request never gets a token, so the grace window gives an attacker nothing.
5. **Refresh cookie:** `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth`. JavaScript
   can't read it (XSS), it is never sent cross-site (CSRF), and it is not sent to the rest
   of the API. Token responses carry `Cache-Control: no-store`.
6. **Every authenticated request loads the user by primary key.** The JWT proves identity;
   the database decides whether the account is still active and what its role is now. A
   disabled user or a changed role takes effect immediately instead of after ≤15 minutes,
   for the cost of one indexed lookup that most endpoints need anyway.
7. **RBAC is a dependency factory** `require_roles(*roles)`; admins are never created via
   the public API (`role` on register accepts only `mentee` / `mentor`), only with
   `make create-admin`.

**Alternatives.**
- *Stateless access-token check (claims only)*: no DB hit, but deactivation and role changes
  lag by up to the token lifetime.
- *Deleting the refresh token on use*: simpler, but a replayed token then looks like an
  unknown one, so theft can't be detected.
- *No grace window*: strictly safer on paper, but every double refresh from two tabs would
  log the user out; the frontend also serializes refreshes, the grace window is the backstop.

**Consequences.** Logout = deleting one key; "log out everywhere" and password reset revoke
every family. Access tokens stay valid until they expire (≤15 min) after logout — accepted,
because they live only in memory on the client. Tests run against a dedicated
`mentorhub_test` database (each test in a rolled-back transaction) and Redis DB 15.

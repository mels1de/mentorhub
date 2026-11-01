# 0005 — Short-lived JWT access tokens + rotating refresh tokens in Redis

**Context.** SPA frontend, several API replicas, need for logout, forced logout
(inactivity, password change, 2FA) and protection against stolen tokens.

**Decision.** Access token: JWT, 15 min, sent in `Authorization: Bearer`, verified
statelessly. Refresh token: opaque random value, httpOnly + Secure + SameSite cookie,
stored (hashed) in Redis with TTL; rotated on every use; reuse of an old refresh token
revokes the whole token family.

**Alternatives.** *Long-lived JWT only*: cannot be revoked. *Server sessions only*: a DB/
Redis lookup on every request, simpler but less common for APIs. *Refresh token in
localStorage*: exposed to XSS.

**Consequences.** Logout and revocation are instant (delete key). Requires the frontend
refresh interceptor and CSRF consideration for the cookie endpoint (SameSite=Strict +
dedicated path).

# 0013 — Frontend session: in-memory access token, refresh interceptor, inactivity logout

**Context.** The SPA must keep users logged in across reloads, renew the 15-minute access
token without the user noticing, work with several open tabs, and log out after inactivity
(brief requirement) — without exposing tokens to XSS.

**Decision.**
- **Access token only in memory** (Pinia store), never in `localStorage`. After a reload
  `bootstrap()` calls `/auth/refresh` with the httpOnly cookie; the router guard waits for
  it, so a logged-in user is never bounced to the login page on F5.
- **Axios interceptor**: adds `Authorization: Bearer`; on `401` with code `invalid_token`
  it refreshes once and replays the request. Other 401s (`invalid_credentials`,
  `invalid_otp`) go straight to the form. Refresh is single-flight in a tab and serialized
  across tabs with the Web Locks API (`navigator.locks`), because tabs share one rotating
  cookie. If refresh fails, the store is cleared and the user lands on the login page with
  `?reason=expired&redirect=...`.
- **Tabs stay in sync** through `BroadcastChannel`: logout in one tab logs out all, login in
  one restores the others, activity in any tab counts as activity.
- **Inactivity logout** (`useInactivityTimer`): 15 min without mouse/keyboard/scroll/touch,
  a warning dialog for the last 2 min; while it is open only "Stay logged in" counts, and on
  `visibilitychange` the timer is re-checked because background tabs throttle intervals.
- **Route meta** `requiresAuth`, `roles`, `guestOnly`; `?redirect=` accepts only same-site
  paths (no open redirect). Email-link tokens are read from the URL fragment and removed
  from the address bar right away.
- **Forms**: VeeValidate + Zod 4 through a 20-line adapter (`lib/zodSchema.ts`), because
  `@vee-validate/zod` still targets Zod 3. The server re-validates everything; 422 field
  errors are mapped back onto the fields.

**Alternatives.**
- *Token in `localStorage`*: survives reloads without a refresh call, but any XSS can steal
  it. *Access token in a cookie too*: then every API call needs CSRF protection.
- *Proactive refresh on a timer*: fewer failed requests, but extra traffic for idle tabs and
  still needs the 401 fallback; the interceptor alone is simpler.
- *Server-side idle timeout only*: can't show a warning, and the refresh token's 7-day
  lifetime is deliberately longer than the idle limit.

**Consequences.** A reload costs one `/auth/refresh` + `/users/me` round-trip. Inactivity
logout is a client-side control: it protects an unattended browser, not against an
attacker holding a token — that is what short access tokens and refresh rotation are for.

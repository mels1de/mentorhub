# API error types

Every error response is [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details
(`Content-Type: application/problem+json`). Domain errors point their `type` at an anchor
below and repeat it as the `code` extension, which clients should switch on. Framework errors
(unknown route, wrong method) use `type: about:blank` and have no `code`.

Every body carries `request_id` (same value as the `X-Request-ID` header); `5xx` responses
never include internal details — search the logs by `request_id` instead.

```json
{
  "type": "https://github.com/mels1de/mentorhub/blob/main/docs/errors.md#not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Skill 42 not found",
  "instance": "/api/v1/skills/42",
  "code": "skill_not_found",
  "request_id": "01a1a5f4-e53b-7666-8571-610396e2a613"
}
```

Feature modules add their own codes here when they subclass these.

## internal_error
`500`. Unexpected server error. No `detail`.

## validation_error
`422`. Request failed schema validation. Extension `errors: [{loc, msg, type}]`; submitted
values are never echoed back.

## invalid_cursor
`422`. The pagination `cursor` is malformed, tampered with, or from another endpoint. Restart
from the first page (omit `cursor`).

## business_rule_violation
`422`. Input is well-formed but breaks a domain rule.

## invalid_link
`422`. An email link (verification, password reset) is unknown, expired, already used, or
replaced by a newer link. Ask for a new email.

## not_authenticated
`401`. Missing or invalid credentials. Carries `WWW-Authenticate: Bearer`.

## invalid_credentials
`401`. Wrong email or password. The same answer for an unknown email, so it can't be used to
find out who is registered.

## invalid_token
`401`. The access token is missing, malformed or expired, or the refresh cookie is missing,
unknown or already used. Clients call `POST /api/v1/auth/refresh` once, then send the user to
the login page.

## refresh_token_reused
`401`. An already-exchanged refresh token was presented again. The whole login session was
revoked because the token may have been stolen; the user has to log in again.

## invalid_otp
`401`. The login code is wrong, or the challenge expired. Extension `attempts_left` when the
code was wrong.

## permission_denied
`403`. Authenticated, but not allowed to do this.

## account_disabled
`403`. The account exists but was deactivated by an admin.

## not_found
`404`. The resource does not exist (or is hidden from this user).

## conflict
`409`. The request conflicts with the current state (duplicate, concurrent change).

## email_not_verified
`422`. 2FA sends codes by email, so it can be enabled only after the email is verified.

## rate_limited
`429`. Too many requests from this client (or for this account). Carries `Retry-After`
(seconds) and the same value as the `retry_after` extension.

## otp_locked
`429`. Too many wrong login codes; the account can't finish a login until `Retry-After`
seconds have passed.

## email_taken
`409`. Registration with an email that already has an account (case-insensitive).

## upstream_error
`502`. An external service (storage, email, captcha, maps, LLM) returned an unusable answer.

## upstream_unavailable
`503`. An external service timed out or is down. Safe to retry later.

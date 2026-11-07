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

## business_rule_violation
`422`. Input is well-formed but breaks a domain rule.

## not_authenticated
`401`. Missing or invalid credentials. Carries `WWW-Authenticate: Bearer`.

## permission_denied
`403`. Authenticated, but not allowed to do this.

## not_found
`404`. The resource does not exist (or is hidden from this user).

## conflict
`409`. The request conflicts with the current state (duplicate, concurrent change).

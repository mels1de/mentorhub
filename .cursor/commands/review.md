# Review my changes

Review the current git diff (`git diff main...HEAD` plus uncommitted changes) as a strict
senior engineer. Check, in this order:

1. Correctness and edge cases (concurrency, None, empty lists, timezones).
2. Security: authz on every route, input validation, secrets, injection, PII in logs.
3. Architecture: layer rules from CLAUDE.md, module boundaries, async correctness.
4. Data: missing indexes/constraints, N+1 queries, migration up/down.
5. Tests: missing cases (401/403/404/409/422), flaky patterns.
6. Naming, typing, readability.

Output a numbered list: severity (blocker/major/minor), file:line, problem, suggested fix.
Do not edit files. Finish with 3 questions a thesis committee could ask about this code.

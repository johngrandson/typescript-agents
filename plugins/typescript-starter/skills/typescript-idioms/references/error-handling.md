# Unknown errors

Catch unknown and narrow expected classes. AppError carries code, status and envelope; storage and worker errors have different responsibilities. Preserve unknown failures and sanitize SQL exposure.

Use finally for cleanup, but do not mask a failure with a cleanup exception or successful fallback. Test known client failures and unexpected programmer errors independently.

## Starter evidence

Read `apps/api/src/core/errors.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

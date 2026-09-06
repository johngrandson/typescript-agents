# Admission and resource limits

Session hardLimit and retention settings are explicit resource controls. createIfBelowLimit enforces atomic admission; a 429 response does not imply a general per-user/IP rate-limiter exists.

Review body size, stream buffering, deadlines and queue admission independently. If rate-limiting is requested, define key, scope and multi-instance behavior, then test it without
fabricating a distributed counter.

## Starter evidence

Read `apps/api/src/core/context.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

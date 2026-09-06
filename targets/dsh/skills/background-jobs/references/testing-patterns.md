# Worker tests

Exercise the shared repository contract in memory and disposable Postgres: atomic claims, stale ownership rejection, expiry, renewal, completion, failure and abandonment. Include
concurrent workers in SQL tests.

Runner tests must check sequential batches, retry backoff, permanent failures, unknown kinds, timeout and shutdown. Do not use fail with a zero delay to represent abandonment.
Preserve evidence when SQL infrastructure cannot run.

## Starter evidence

Read `packages/db/src/__tests__/job-lease.contract.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed
source hashes before adapting them.

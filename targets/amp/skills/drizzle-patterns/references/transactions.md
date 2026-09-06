# Atomic mutations and revisions

Session writes return value plus revision and updatedAt metadata from the same mutation. Admission and ordered item changes need transaction-level protection. A service-side count
followed by insert is not atomic.

Inspect lock scope and SQL statement ordering in the Drizzle adapter. Verify concurrent callers, rollback and no event publication after a failed write. Memory parity is necessary
but only real Postgres tests establish locking behavior.

## Starter evidence

Read `packages/db/src/session-revision.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes
before adapting them.

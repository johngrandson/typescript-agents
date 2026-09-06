---
name: psql-query
description: Inspect local PostgreSQL state with read-only SQL for session, job and query diagnostics.
---

# PostgreSQL Diagnostics

Use the existing PostgreSQL schema in `packages/db`; resolve the configured
local database through `packages/env` and never print credentials.

## Rules

1. NEVER reset a database or run against production.
2. Confirm the requested local database and use a read-only transaction.
3. Read the schema before naming tables, columns or indexes.
4. Avoid returning session payloads, credentials or other sensitive row data.

## Workflow

1. Inspect the relevant Drizzle schema and migration in `packages/db`.
2. Check that `DATABASE_URL` refers to the intended local diagnostic database.
3. Execute one bounded query using `psql` with `ON_ERROR_STOP` and a read-only
   transaction; limit returned rows. Explain query plans without executing
   writes or using `EXPLAIN ANALYZE` on mutating statements.
4. Prefer a disposable database and the repository integration tests for
   reproducing a write-path bug. Never reuse development data as a test fixture.
5. Report the query, result and what remains unverified.

```bash
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 \
  -c 'BEGIN READ ONLY; SELECT current_database(); COMMIT;'
```

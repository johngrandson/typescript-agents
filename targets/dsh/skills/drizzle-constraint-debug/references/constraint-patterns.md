# Constraint failure taxonomy

Inspect a DrizzleQueryError cause for SQLSTATE through the existing safe error boundary. Codes 23505, 23503, 23514 and 23502 correspond to unique, foreign-key, check and not-null
failures. Avoid logging driver messages with SQL parameters.

Trace the named constraint to schema and migration, then every write path. Distinguish missing migrations, invalid legacy data and races. Reproduce in disposable Postgres before
changing constraints or converting a database error to AppError.

## Starter evidence

Read `packages/db/src/errors.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

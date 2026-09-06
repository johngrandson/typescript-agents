# Reviewed migrations

Use pnpm db:generate with the installed Drizzle config and loader. Review generated SQL, snapshot metadata and journal order in packages/db/drizzle. Never edit an applied migration
to hide an inconsistent database.

Run migration and upgrade scenarios on disposable Postgres, including the previous schema and existing records. Consider locks, backfills, uniqueness and rollout order. db:push
changes schema directly and is not a replacement for reviewed migrations; never reset a database without authorization.

## Starter evidence

Read `packages/db/drizzle.config.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

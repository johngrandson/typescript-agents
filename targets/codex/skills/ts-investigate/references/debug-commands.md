# Investigation commands

Read the nearest manifest first. From the monorepo root, run the affected workspace check-types and `pnpm --filter <package> test:run <test-path>`. Confirm actual package names and
test paths; do not pass flags from a different test runner.

Use rg for the error code, symbol, imports and shared schema. Inspect git diff/log for recent changes. Check the running process and generated output before assuming edited source
is active. Read configured structured logs rather than a guessed log/dev path.

Use Fastify app.inject for HTTP reproduction, shared repository contracts for storage, disposable Postgres for races/migration errors, and client/worker lifecycle tests for async
bugs. Do not remove dependency/build directories, reinstall packages or mutate a live database as a default debugging step.

# Verified patterns to remember

- Keep runtime schema and static DTO together through TypeBox/Static; casts do not validate JSON.
- Services and repository ports are intentional. Worker code cannot import API modules.
- Web mutations use Server Actions; mobile uses REST and legitimate loading hooks. DOM UI cannot render as native components.
- applySessionEvent stays pure/shared; stale requests and stream recovery require ownership checks.
- Postgres/memory contracts must agree, while only Postgres tests demonstrate locks and migrations.
- Jobs run sequentially with fenced leases and at-least-once delivery. batchSize is not concurrency, and fail with zero delay is not abandon.
- Catch unknown, narrow the expected error and rethrow unexpected failures. Sanitize SQL values in logs.

Save a lesson only after a verified fix or explicit user instruction. Cite the test/source/version, search existing knowledge, preserve hand-authored material and keep one
canonical library skill per package/scope.

---
name: background-jobs
description: Use when editing the custom Postgres job queue, worker handlers, registry, retries, leases, recurrence, idempotency, or shutdown behavior.
effort: medium
user-invocable: false
paths:
- apps/worker/src/**/*.ts
- packages/db/src/*job*.ts
- packages/db/src/__tests__/*job*
---

# Background jobs

The starter has a custom Postgres-backed queue and a Node worker. Read `apps/worker/src/registry.ts`, `runner.ts`, `handlers`, `packages/db/src/repository.ts` and `drizzle-job-repository.ts`.

## Usage

```text
pnpm --filter @starter/worker test:run
pnpm test:postgres
```

## Runtime contract

- `JobRunner` is sequential: `batchSize` bounds executions per tick, and jobs are claimed one at a time. It is not a concurrency setting.
- Claim is atomic and uses `FOR UPDATE SKIP LOCKED`. Ownership token plus an unexpired lease fences acknowledgements. `renew`, `complete`, `fail` and `abandon` must reject stale owners.
- Delivery is at-least-once. Handlers must be idempotent across retry, restart and ambiguous acknowledgements. A completed side effect followed by a failed acknowledgement may execute again.
- `PermanentJobError` marks malformed payloads or other non-retryable failures; `abandon` is terminal. `fail(..., 0)` schedules another attempt and must not substitute for permanent failure.
- Retry backoff is bounded; `maxAttempts` includes executed attempts. Recurrence has a stable key and persisted history; terminal histories do not revive on restart. Do not install
  Redis or a third-party queue to match an old framework example.
- Handler/RPC/shutdown deadlines must fit within the lease. Await active work and stop polling before closing storage; cancellation is cooperative, not proof that I/O ended.
- Handlers use `JobContext.repositories` and `enqueue`, never API modules or the API event bus. The worker has no direct access to that in-memory bus.

## Existing handler

`createArchiveSessionHandler` validates a UUID payload and job identity, then publishes an immutable `session-{id}-job-{jobId}.json`. A retry validates an existing archive before
treating it as success. It checks `ctx.signal` around I/O and preserves unexpected storage errors.

## Tests

Test first execution, duplicate delivery, malformed payload, missing session, lease expiry, stale acknowledgement, timeout, shutdown and recurrence restart. Run memory job contract
suites and disposable Postgres suites; a memory test cannot establish concurrent SQL fencing.

## Starter example

This excerpt uses the existing implementation; read its source for imports and setup.

Source: `packages/db/src/repository.ts`.

```typescript
export interface JobOwnership {
  id: string;
  token: string;
}

export interface ClaimedJob extends JobRecord {
  leaseExpiresAt: Date;
  ownershipToken: string;
}
```

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. NEVER bypass tests or reset a database to obtain a passing result.

## Apply the reference

1. Read the handler registry and repository ownership contract before changing a job kind.
2. Validate malformed payloads and duplicate delivery with the existing archive handler tests.
3. Run the worker tests and disposable Postgres lease/recurrence suites for affected behavior.
4. Record the observed retry, abandonment and shutdown results, including unavailable SQL coverage.

## References

- [Recurrence patterns](references/recurrence-patterns.md)
- [Queue config](references/queue-config.md)
- [Testing patterns](references/testing-patterns.md)
- [Worker patterns](references/worker-patterns.md)

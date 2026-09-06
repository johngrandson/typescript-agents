# Reference example verification

The catalog records source examples from `typescript_starter`, captured on
2026-09-05. The snapshot manifest is [starter-snapshot.json](starter-snapshot.json).
Its 405 file hashes and aggregate digest identify the captured bytes, including
local changes. The catalog pairs 23 excerpts with source hashes and test paths.

The observations below were recorded on 2026-09-05 against that capture.
They are retained as evidence for the source examples. They are not fresh
executions against the current application or the harness.

## Captured test observations

| Run | Passing tests | Duration in seconds |
| --- | ---: | ---: |
| types-contracts | 54 | 1.18 |
| api-sessions | 26 | 4.64 |
| memory-and-isolation | 112 | 1.04 |
| postgres-and-migrations | 112 | 22.21 |
| web-server-actions | 22 | 3.31 |
| web-sse-recovery | 24 | 1.02 |
| mobile-service | 22 | 2.13 |
| mobile-store-and-hook | 28 | 1.29 |
| worker-retry-idempotency | 50 | 3.47 |

These nine commands completed with exit code zero. The total is 450 test
executions; overlapping suites are not additional unique coverage. Commands
run from the captured application root with its frozen dependencies.

### types-contracts

```sh
pnpm --filter @starter/types exec vitest run src/__tests__/session-inputs.test.ts src/__tests__/response-envelopes.test.ts src/__tests__/session-projection.test.ts
```

### api-sessions

```sh
pnpm --filter @starter/api exec vitest run src/modules/sessions/__tests__/service.test.ts src/modules/sessions/__tests__/routes.test.ts
```

### memory-and-isolation

```sh
pnpm --filter @starter/db exec vitest run src/__tests__/repositories.test.ts src/__tests__/disposable-postgres.test.ts
```

### postgres-and-migrations

```sh
pnpm --filter @starter/db test:postgres
```

### web-server-actions

```sh
pnpm --filter @starter/web exec vitest run lib/__tests__/action-results.test.ts
```

### web-sse-recovery

```sh
pnpm --filter @starter/web exec vitest run lib/__tests__/sse-proxy.test.ts lib/__tests__/session-stream.test.ts
```

### mobile-service

```sh
pnpm --filter @starter/mobile exec vitest run src/services/__tests__/apiService.test.ts
```

### mobile-store-and-hook

```sh
pnpm --filter @starter/mobile exec vitest run src/store/__tests__/sessionsStore.test.ts src/screens/SessionDetail/__tests__/useSessionDetail.test.ts src/screens/SessionDetail/__tests__/loadOwnership.test.ts src/screens/SessionDetail/__tests__/recovery.test.ts
```

### worker-retry-idempotency

```sh
pnpm --filter @starter/worker exec vitest run src/__tests__/runner.test.ts src/__tests__/leases.test.ts src/handlers/__tests__/archive-session.test.ts
```

## Reproduction and limits

Obtain source bytes matching the manifest and check them before rerunning:

```sh
python3 -m scripts.starter_snapshot --check \
  --copy /path/to/captured-starter \
  --manifest docs/reference/starter-snapshot.json
```

The application HEAD alone is insufficient because the capture includes
local changes. Snapshot checking takes an explicit copy path; it does not
depend on the capture machine or an archived temporary directory.

The PostgreSQL command uses the application fixture for disposable databases.
It is separate from the harness offline checks. Browser E2E, mobile device
runs and deployment are not covered by these observations.

The harness content suite checks the required example categories, complete
source copies, source/test hashes, excerpts and these evidence references.
It does not rerun the application suites or start a database.

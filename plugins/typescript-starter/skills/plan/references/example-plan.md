# Example plan: verify Session archive reliability

This is an instructional plan built from existing starter capabilities, not a claim that the captured implementation has these defects.

**Status**: PENDING
**Detail Level**: standard
**Input**: example acceptance criteria

## Summary

Verify one immutable archive per job identity across duplicate delivery and shutdown. Preserve the current sequential runner and repository ownership contract.

## Scope and decisions

Read apps/worker/src/handlers/archive-session.ts, runner.ts, registry.ts and packages/db/src/repository.ts. Reuse createJsonDocumentStore and the existing queue. No API imports,
Redis, account identity or distributed event publication.

| Decision | Choice | Reason |
| --- | --- | --- |
| Publication identity | sessionId plus job.id | Retry observes the same immutable effect |
| Permanent invalid data | PermanentJobError | Retrying cannot repair malformed payload |
| Ownership | Token plus unexpired lease | Stale workers cannot acknowledge |

## Phase 1: Contract and storage [PENDING]

- [ ] [P1-T1][drizzle] Read shared lease/idempotency contracts and identify coverage gaps.
  **Locations**: `packages/db/src/__tests__/job-lease.contract.ts`
  **Acceptance**: stale ownership cannot complete/renew; memory and Postgres agree.
- [ ] [P1-T2][jobs] Check archive identity and validation before treating existing output as success.
  **Locations**: apps/worker/src/handlers/archive-session.ts
  **Acceptance**: a duplicate job yields the same validated immutable archive.

## Phase 2: Independent verification [PENDING]

### Parallel: isolated tests

- [ ] [P2-T1][test] Exercise malformed payload, missing session and conflicting archive.
- [ ] [P2-T2][test] Exercise active claim/handler shutdown without closing storage early.

### Sequential

- [ ] [P2-T3][direct] Consolidate results and fix only observed defects within scope.

## Phase 3: Final gate [PENDING]

- [ ] [P3-T1][test] Run worker check-types/lint/test:run and disposable Postgres contracts.
- [ ] [P3-T2][test] Run pnpm verify once after final changes.

## Verification commands

```bash
pnpm --filter @starter/worker check-types
pnpm --filter @starter/worker lint
pnpm --filter @starter/worker test:run
pnpm test:postgres
pnpm verify
```

## Risks and handoff

A timed-out promise does not prove I/O stopped. Ambiguous completion must not fall through to another retry acknowledgement. Persist decisions, failed attempts and next unchecked
task in scratchpad.md. Missing database infrastructure is BLOCKED/NOT RUN, not success. Review only after implementation evidence exists; report all remaining criteria.

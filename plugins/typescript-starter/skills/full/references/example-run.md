# Example Full Cycle Run

## Session Revision Handling

This transcript illustrates the workflow using existing Session contracts.
Its retries, findings and counts demonstrate output structure; they are not
results of a run against the starter. An actual run reports only observed
changes and verification evidence.

```text
$ /ts:full Verify session revision handling across API and clients

[INITIALIZING] Creating feature branch: feature/session-revisions
[DISCOVERING] Scanning codebase for patterns...
  Complexity: HIGH — repository receipts, API events, two client transports
  User choice: "research it"

[PLANNING] Spawning 4 research agents (comprehensive)...
  ✓ starter-patterns-analyst: Mapped SessionService and repository ownership
  ✓ drizzle-schema-designer: Traced persisted revision and migration history
  ✓ react-architect: Separated web SSE and mobile WS recovery paths
  ✓ node-runtime-advisor: Reviewed event ordering and connection cleanup
[PLANNING] Creating implementation plan...
  Phase 1: Revision Storage (3 tasks)
  Phase 2: Session Service (4 tasks)
  Phase 3: Client Recovery (5 tasks)
  Phase 4: Tests (4 tasks)
[PLANNING] Written: .claude/plans/session-revisions/plan.md

[WORKING] Phase 1: Revision Storage
  ✓ Task 1/3: Check sessions.revision and its safe-integer constraint
  ✓ Task 2/3: Check the Drizzle migration journal
  ✓ Task 3/3: Verify memory/Postgres receipt parity
[WORKING] Phase 1 complete, checkpoint recorded

[WORKING] Phase 2: Session Service
  ✓ Task 1/4: Wire SessionService
  ✓ Task 2/4: Implement session creation
  ✗ Task 3/4: Preserve committed session mutation receipts (retry 1/3)
  ✓ Task 3/4: Preserve committed session mutation receipts
  ✓ Task 4/4: Keep revision metadata out of public SessionSnapshot DTOs
[WORKING] Phase 2 complete, checkpoint recorded

[WORKING] Phase 3: Client Recovery
  ✓ Task 1/5: Check web use-session-events processing
  ✓ Task 2/5: Check mobile websocketService recovery
  ✓ Task 3/5: Preserve stale-request ownership checks
  ✓ Task 4/5: Verify pending and error states for mutations
  ✓ Task 5/5: Verify connection cleanup on navigation
[WORKING] Phase 3 complete, checkpoint recorded

[WORKING] Phase 4: Tests
  ✓ Task 1/4: Repository contract tests on memory and disposable Postgres
  ✓ Task 2/4: SessionService committed-receipt tests
  ✓ Task 3/4: Web event-validation tests
  ✓ Task 4/4: Mobile recovery and load-ownership tests
[WORKING] Phase 4 complete, checkpoint recorded

[VERIFYING] pnpm verify: PASS

[REVIEWING] Spawning 4 review agents...
  ✓ typescript-reviewer: 1 finding about mutation receipt provenance
  ✓ testing-reviewer: PASS
  ✓ security-analyzer: PASS on the implemented input boundaries
  ✓ verification-runner: Confirmed current verification evidence

[REVIEWING] Adding the finding to the plan...
[WORKING] Preserving the receipt returned by the committed mutation...
  ✓ Added a regression assertion for interleaved writes
[VERIFYING] pnpm verify: PASS
[REVIEWING] Re-review passed

[LEARNING] Captured: "Publish the committed mutation receipt without re-reading newer state"

## Feature Complete

**Feature**: Session revision handling
**Duration**: {measured duration}
**Files Modified**: {actual count}
**Tests Added**: {actual count}

<promise>DONE</promise>
```

Read the current source before using this example:

- `packages/db/src/schema.ts` and `packages/db/drizzle/0004_session_revisions.sql`
- `apps/api/src/modules/sessions/service.ts` and `__tests__/service.test.ts`
- `apps/web/components/session-panel/hooks/use-session-events.ts`
- `apps/mobile/src/services/websocketService.ts` and `__tests__/websocketRecovery.test.ts`

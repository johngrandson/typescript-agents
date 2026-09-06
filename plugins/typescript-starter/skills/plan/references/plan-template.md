# Plan Template Format

## Full Plan Template

```markdown
# Plan: {Feature Name}

**Status**: PENDING
**Created**: {date}
**Detail Level**: {quick|standard|deep}
**Input**: {review path, or "from description"}

## Summary

{What we're building in 2-3 sentences}

## Scope

**In Scope:**

- Item 1
- Item 2

**Out of Scope:**

- Item 1

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Library | {name} | {why} |
| Storage | {type} | {why} |

## Data Model

{If database changes needed}

## Module Structure

{If new modules needed}

## System Map (React features with 2+ pages/components only)

{Omit this entire section for non-React or simple features.
Include when the react-architect produced a breadboard.}

### Places

| ID | Place | Entry Point | Notes |
|----|-------|-------------|-------|
| P1 | {ReactName} | {route} | {notes} |

### UI Affordances

| ID | Place | Component | Affordance | Type | Wires Out | Returns To |
|----|-------|-----------|------------|------|-----------|------------|
| U1 | P1 | {comp} | {element} | {event/action} | {N-id} | {S-id} |

### Code Affordances

| ID | Place | Module | Affordance | Wires Out | Returns To |
|----|-------|--------|------------|-----------|------------|
| N1 | P1 | {Module} | {function} | {targets} | {S-id} |

### Data Stores

| ID | Store | Type | Read By | Written By |
|----|-------|------|---------|------------|
| S1 | {name} | {type} | {U/N ids} | {N ids} |

### Spikes

{List any ⚠️ unknowns from the tables above.}

## Phase 0: Spikes [PENDING] (only if ⚠️ unknowns exist)

- [ ] [P0-T1][direct] Spike: {investigate unknown}
  **Unknown**: {what we don't know}
  **Success criteria**: {what resolves it}
  **Time-box**: 30 minutes max

## Phase 1: {Phase Name} [PENDING]

- [ ] [P1-T1][drizzle] Extend the required repository operation and both adapters.
  **Implementation**: Follow packages/db/src/repository.ts and contract suites.
  **Acceptance**: Complete DTOs, atomic revision metadata and memory/Postgres parity.

- [ ] [P1-T2][direct] Update shared TypeBox schemas and Static-derived DTOs.
  **Locations**: packages/types/src/schemas and contract exports.
  **Acceptance**: Runtime validation and all consumers agree.

## Phase 2: {Phase Name} [PENDING]

- [ ] [P2-T1][react] Connect the operation to the intended client.
  **Implementation**: Web Server Action or mobile REST service, matching the workspace.
  **Acceptance**: Pending/error behavior, event projection and cleanup remain correct.

### Parallel: {Group Name}

- [ ] [P2-T2][direct] Task that can run in parallel
- [ ] [P2-T3][direct] Another parallel task

### Sequential

- [ ] [P2-T4][react] Task that depends on above

## Phase N: Verification [PENDING]

- [ ] [PN-T1][test] Unit tests for {context}
- [ ] [PN-T2][test] React tests for {component}
- [ ] [PN-T3][test] Run full verification suite

## Task Agent Annotations

| Annotation | Agent | Use For |
|------------|-------|---------|
| `[drizzle]` | drizzle-schema-designer | Schemas, migrations, queries |
| `[react]` | react-architect | React, real-time UI, event bus |
| `[jobs]` | background-jobs-specialist | Background jobs, workers |
| `[runtime]` | node-runtime-advisor | Async tasks and resource lifecycle |
| `[security]` | security-analyzer | Auth, tokens, permissions |
| `[test]` | testing-reviewer | Tests, mocks, factories |
| `[direct]` | (none) | Simple tasks, config |

**Rules:** Primary focus wins. Security always wins for auth tasks.

## Files to Follow as Patterns

Existing files to read first when implementing (reduces cold-start):

- `{path/to/similar_module.ts}` — follow this pattern for {reason}
- `{path/to/existing_test.test.ts}` — follow this test structure
- `{path/to/component.ts}` — follow this component pattern

## Patterns to Follow

From codebase analysis:

- {Pattern 1}
- {Pattern 2}

## Session Handoff

Key context from planning session for `/ts:work` to use:

- **Discovery**: {key findings, bugs found, gotchas learned}
- **Decisions**: {choices made and why}
- **Warnings**: {things to watch out for during implementation}

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| {potential issue} | {how to handle} |

## Verification Checklist

- [ ] `pnpm check-types` passes
- [ ] `pnpm lint` passes
- [ ] `pnpm test:run` passes
- [ ] `pnpm verify` passes after final changes

```

## Task Granularity

Tasks are logical work units, NOT individual file edits.

**BAD** (too atomic -- one task per file):

```markdown
- [ ] [P3-T3][direct] Replace page.waitForTimeout in file_a.test.ts
- [ ] [P3-T4][direct] Replace page.waitForTimeout in file_b.test.ts
- [ ] [P3-T5][direct] Replace page.waitForTimeout in file_c.test.ts
```

**GOOD** (grouped by pattern with locations and implementation):

```markdown
- [ ] [P3-T2][direct] Replace only observed timing-dependent waits with
  assertions on the expected behavior.
  **Locations**: List exact affected test files and lines from the current diff.
  **Pattern**: Choose the assertion library already used by that workspace:
  - Browser: `await expect(page.getByRole('button', { name: 'Create session' })).toBeEnabled()`
  - React: `await screen.findByText('Session created')` when that message is the expected UI
  - Service: await the mutation, then inspect the isolated event-bus fixture's received events
  **Reference**: `apps/api/src/modules/sessions/__tests__/service.test.ts` awaits
  `h.service.addItem(session.id, { kind: 'note', label: 'a', value: '' })`
  before asserting the `item_added` event.
```

**Guidelines:**

- 3-8 tasks per phase (not 15+)
- Group by PATTERN, list LOCATIONS within
- Include implementation detail: code examples, before/after
- Sub-locations are indented lists, not separate tasks
- Each task completable in one sitting

**IMPORTANT**: Plan template does NOT auto-start `/ts:work`. The
skill presents the plan and asks the user how to proceed.

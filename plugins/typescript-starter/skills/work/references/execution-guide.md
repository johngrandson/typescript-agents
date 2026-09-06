# Execution Guide

Step-by-step execution details for `/ts:work`.

## Contents

- [Loading a Plan](#loading-a-plan)
- [Task Routing](#task-routing)
- [Parallel Task Execution](#parallel-task-execution)
- [Verification](#verification)
- [Proactive Patterns](#proactive-patterns)
- [Checkpoint Pattern](#checkpoint-pattern)
- [Phase Transitions](#phase-transitions)
- [Git Integration](#git-integration)
- [Error Recovery](#error-recovery)

## Loading a Plan

Read the plan file and count progress:

```markdown
## Phase 1: Schema Design [COMPLETED]
- [x] [P1-T1][drizzle] Create sessions migration
- [x] [P1-T2][drizzle] Add indexes

## Phase 2: Session Service [IN_PROGRESS]
- [x] [P2-T1][direct] Wire SessionService with the existing contract/service/repository pattern
- [ ] [P2-T2][drizzle] Add session revision field    <-- NEXT TASK
- [ ] [P2-T3][direct] Implement session creation
```

**Task ID format**: `[Pn-Tm]` where n=phase, m=task number.

With `--from P2-T3`: Skip directly to that task.

## Task Routing

### Primary: Parse Agent Annotation

Task format: `- [ ] [Pn-Tm][agent] Description`

```markdown
- [ ] [P2-T2][drizzle] Add session revision field to schema
                ^^^^
           Parse this annotation -> spawn drizzle-schema-designer
```

### Routing Table

| Annotation | Agent | Verification |
|------------|-------|--------------|
| `[drizzle]` | drizzle-schema-designer | migrate + test |
| `[react]` | react-architect | test + browser |
| `[jobs]` | background-jobs-specialist | test + manual |
| `[runtime]` | node-runtime-advisor | test |
| `[security]` | security-analyzer | test + audit |
| `[test]` | testing-reviewer | test only |
| `[direct]` | (none) | compile + format |

### Fallback: Keyword Matching (Legacy Plans)

If no `[agent]` annotation, fall back to keywords:

| Keywords (priority order) | Agent |
|---------------------------|-------|
| auth, login, password, token, permission | security-analyzer |
| schema, migration, field, validation result | drizzle-schema-designer |
| worker, job, queue | background-jobs-specialist |
| async, timer, lifecycle, process | node-runtime-advisor |
| react, component, screen | react-architect |
| test, assert, mock | testing-reviewer |
| (no match) | (direct execution) |

**Security priority**: Security keywords ALWAYS win, even if other
patterns match.

### `[direct]` Task Guidance

Tasks annotated `[direct]` are simple and don't need a specialist:

- **Config changes**: Adding env vars, updating `packages/env/src`
- **Dependencies**: Reviewing package/importer changes through /ts:deps-update; frozen installs verify the resulting lock
- **Scaffolding**: Creating directory structure, empty modules
- **Simple wiring**: Adding routes, imports, aliases
- **File operations**: Moving, renaming, or deleting files

Implement these directly without spawning a Task agent. Run
verification (compile + format) after each one.

## Parallel Task Execution

Tasks under `### Parallel:` header execute via subagents:

### Detection

```markdown
## Phase 2: Forms [IN_PROGRESS]

### Parallel: Deal Forms
- [ ] [P2-T1][direct] Add selectors to web Session form
- [ ] [P2-T2][direct] Add selectors to mobile Session form
- [ ] [P2-T3][direct] Add selectors to shared contract fixture

### Sequential
- [ ] [P2-T4][direct] Update shared form helpers
```

Tasks are parallelizable if they:

- Are under a `### Parallel:` header
- Modify different files (check Locations in task description)
- Don't share mutable state (schemas, helpers)

### Spawning Pattern

Spawn ALL parallel tasks in ONE message using the Agent tool:

```
Agent({
  subagent_type: "general-purpose",
  prompt: "Implement P2-T1: Add Session status selectors to
    web Session form at apps/web/components/session-panel/{target-component}.tsx.
    [full task context here]",
  run_in_background: true
})
Agent({
  subagent_type: "general-purpose",
  prompt: "Implement P2-T2: Add selectors to mobile Session form...",
  run_in_background: true
})
// ... one per parallel task
```

### Waiting and Checkpoint

After spawning, wait for ALL agents to complete, then run phase checkpoint:

```bash
pnpm --filter <workspace> lint:fix
pnpm check-types
pnpm --filter <workspace> test:run <affected_test_files>
pnpm lint
```

Mark all completed task checkboxes in the plan.

### When NOT to Parallelize

- Tasks that edit the same file
- Tasks that depend on each other's output
- Schema/migration tasks sharing the same migration journal
- Tasks with `[security]` annotation (need careful review)

## Verification

### After Each Task

```bash
pnpm --filter <workspace> lint
pnpm check-types
```

Use available local logs or isolated runtime probes to detect behavior not covered by typechecking. No application-inspection MCP is installed. Keep resource ownership and actual
checkout/process identity explicit.

### After Each Phase (Full)

```bash
pnpm check-types
pnpm --filter <workspace> test:run <affected_test_files>
pnpm lint
```

### Per-Feature Behavioral Smoke Test

Use existing isolated fixtures by task annotation:

| Annotation | Smoke |
| --- | --- |
| `[drizzle]` | Shared memory/Postgres contract and migration upgrade |
| `[react]` | Web action/SSE or mobile REST/WS interaction and cleanup |
| `[jobs]` | Handler retry/idempotence and stale lease acknowledgement |
| `[security]` | Relevant input/error/path or implemented permission boundary |
| `[direct]` | Nearest package behavior test |

Use disposable infrastructure for mutations. Browser smoke does not establish native rendering and a missing auth system cannot be treated as an installed test target.

### After ALL Phases (Final Gate)

```bash
pnpm verify  # full type, lint, test and unused-code checks
```

### Domain-specific verification

SQL changes require parity and disposable Postgres evidence. UI changes preserve platform-specific transport and stale ownership. Jobs preserve leases, recurrence and at-least-once
idempotency. Security changes validate the real trust boundary.

After 3 failed attempts, create a BLOCKER and record failed approaches in scratchpad.md.

## Proactive Patterns

### Factory Updates for Required Fields

When a shared schema gains a required field, locate affected fixtures and DTO projections first. Update each valid fixture intentionally, preserving tests that exercise
missing-field rejection. Then run the contract and consumer suites.

### Module Existence Check

When a plan says "create new module" or "extract to new module":

1. FIRST check if the module already exists:

   ```bash
   rg -n "export (class|function|interface)" apps packages
   ```

2. If it exists, add to the existing module instead of creating a
   duplicate file (causes compilation errors from duplicate definitions)

## Checkpoint Pattern

After each task passes verification:

1. **Update plan**: Mark checkbox `- [x] [Pn-Tm]...` and **append
   implementation note** — key decisions, gotchas, actual values.
   Example: `- [x] [P2-T2] Add session revision — bounded integer persisted by both repository adapters`
   These notes survive context compaction since the plan is re-read on resume.
2. **Complete Claude Code task**: `TaskUpdate({taskId, status: "completed"})`
   This updates the live progress indicator visible in the UI.
3. **Update phase status**: If all tasks done, change to `[COMPLETED]`
4. **Log progress**: Append to `.claude/plans/{feature}/progress.md`
5. **Start next task**: `TaskUpdate({nextTaskId, status: "in_progress"})`
   then move to next unchecked task

### Progress Log Entry

```markdown
## 14:32 - Task Completed [P2-T2]

**Task**: Add session revision field to schema
**Files Modified**: packages/db/src/schema.ts, packages/db/drizzle/{generated-migration}.sql
**Verification**: PASS (type checks, lint, tests)
```

## Phase Transitions

**CRITICAL: Auto-continue between phases.** When all tasks in a
phase complete, mark it `[COMPLETED]` and IMMEDIATELY start the
next phase. Do NOT stop to ask the user. Do NOT output a summary
between phases. Just keep going until all phases are done or a
BLOCKER is hit.

```markdown
# Before
## Phase 1: Schema Design [IN_PROGRESS]
- [x] [P1-T1] Create sessions migration
- [x] [P1-T2] Add indexes
- [x] [P1-T3] Create schema module

# After
## Phase 1: Schema Design [COMPLETED]
- [x] [P1-T1] Create sessions migration — revision starts at zero and stays within the safe integer range
- [x] [P1-T2] Add indexes — sessions_last_read_at_idx supports the idle-session reaper
- [x] [P1-T3] Create schema module — SessionSnapshot remains a public DTO; mutation receipts carry revision metadata

## Phase 2: Session Service [IN_PROGRESS]  <-- Auto-start immediately
```

## Git Integration

### Commit Strategy

Don't commit after every task. Instead:

1. **After each phase**: Offer to create commit with phase summary
2. **After blockers**: Commit working state before human intervention
3. **After completion**: Ask user about final commit

### Branch Strategy (for /ts:full)

```bash
git checkout -b feature/{feature-slug}
# ... phases execute ...
# On completion, ready for PR
```

## Error Recovery

### Auto-Fix (Common Errors)

| Error Pattern | Auto-Fix |
|--------------|----------|
| `pnpm lint:fix` diff | Run `pnpm lint:fix` |
| Unused variable | Prefix with `_` |
| Missing import | Add import statement |

### Retry with Context

If first attempt fails, retry with error context in the prompt.

### Escalate to BLOCKER

After 3 failures, create blocker in progress file:

```markdown
## BLOCKER

**Task ID**: P2-T3
**Description**: Implement session creation
**Attempts**: 3

**Error History**:
1. Type error: SessionService.create requires a CreateSessionInput argument
2. Test failure: expected TOO_MANY_REQUESTS when the session hard limit is reached
3. Test failure: concurrent creation persisted more sessions than the configured hard limit

**Suggested Actions**:
- Review the isolated repository fixture and configured hard limit
- Check SessionService.create(input: CreateSessionInput): Promise<SessionSnapshot>
- Verify createIfBelowLimit is atomic in both memory and Postgres adapters

**Resume**: `/ts:work plan.md --from P2-T3`
```

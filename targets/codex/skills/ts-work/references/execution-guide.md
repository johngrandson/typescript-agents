# Execution Guide

Step-by-step execution details for `$typescript-starter:ts-work`.

## Contents

- [Loading a Plan](#loading-a-plan)
- [Concern Guidance](#concern-guidance)
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

## Concern Guidance

Annotations such as `[drizzle]`, `[react]`, `[jobs]`, `[runtime]`, `[security]`,
`[test]`, and `[direct]` describe implementation concerns and required checks.
They are not custom-agent identities and never route work to a named worker.
Execute in the current session by default. A native generic worker is optional
only for an independent task with disjoint files and a complete verification
contract.

| Annotation | Guidance and required verification |
|---|---|
| `[drizzle]` | Drizzle safety; migrate/rollback as applicable plus focused tests |
| `[react]` | React lifecycle/security; focused React test plus local/manual UI smoke |
| `[jobs]` | Idempotency and args; worker test plus enqueue behavior check |
| `[runtime]` | Cancellation/concurrency; focused async lifecycle tests |
| `[security]` | Authorization/input handling; negative-path tests and audit |
| `[test]` | Test quality; run the named focused test |
| `[direct]` | General implementation; format and compile plus affected test |

Legacy unannotated tasks use their subject matter to select the same concern
guidance, never a worker identity. Security requirements take priority.

## Parallel Task Execution

Tasks under `### Parallel:` are eligible for optional generic workers or sequential execution:

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

### Execution Pattern

Native generic subagents are optional for tasks that are independent and touch
different files. Give each worker the full task text, locations, constraints,
and verification contract, and wait for all workers before checkpointing.
Do not require annotation-named custom agents.

If native subagents are unavailable, execute every task sequentially in plan
order in this session. This fallback is complete: apply the same domain guidance,
verification, checkbox update, implementation note, and progress-log entry for
each task. Never skip a task because parallel execution is unavailable.

### Waiting and Checkpoint

If optional workers were used, wait for all of them; otherwise, after the sequential tasks complete, run the phase checkpoint:

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
2. **Log completion**: Append the task ID, changed files, and verification result to `progress.md`.
3. **Update phase status**: If all tasks done, change to `[COMPLETED]`
5. **Start next task**: Log its start, then select the next unchecked
   non-`[BLOCKED]` task. Stop if an unresolved blocker precedes it unless
   `--skip-blockers` was explicitly supplied

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

### Branch Strategy (for $typescript-starter:ts-full)

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

After 3 failures, keep the plan row unchecked, append `[BLOCKED]`, and
optionally mark its phase `[BLOCKED]`. Append the attempts and error evidence to
`.claude/plans/{slug}/progress.md`, write the dead end to `scratchpad.md`, and
stop by default. Continue to later work only with explicit `--skip-blockers`.

```markdown
- [ ] [P2-T3][drizzle] [BLOCKED] Implement session creation

## BLOCKER: P2-T3
**Attempts**: 3
**Error history**: {commands and first actionable failures}
**Suggested next action**: {evidence-based recommendation}
```

Retry this task explicitly with the native `ts-work` invocation and
`--from P2-T3`; clear `[BLOCKED]` when starting that retry.

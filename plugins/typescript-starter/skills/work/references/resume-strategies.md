# Resume Strategies

## How State Works

**Plan checkboxes ARE the state.** No separate JSON state files.

- `[x]` = completed
- `[ ]` = pending
- Phase status `[COMPLETED|IN_PROGRESS|PENDING]` tracks phase progress
- BLOCKERs in progress file track failed tasks

## Resume Modes

### Default: Auto-detect

```
/ts:work  # Find most recent IN_PROGRESS plan, resume from first [ ]
```

### From Specific Task

```
/ts:work .claude/plans/session-creation/plan.md --from P2-T3
```

Skips directly to P2-T3 regardless of earlier unchecked tasks.

### Skip Blockers

```
/ts:work .claude/plans/session-creation/plan.md --skip-blockers
```

Continues past tasks that previously failed with BLOCKER status.

## Resume from Interrupted Session

On resume, the plan file itself shows progress:

```markdown
## Phase 1: Schema Design [COMPLETED]
- [x] [P1-T1][drizzle] Create sessions migration
- [x] [P1-T2][drizzle] Add indexes

## Phase 2: Session Service [IN_PROGRESS]
- [x] [P2-T1][direct] Wire SessionService
- [ ] [P2-T2][drizzle] Add session revision     <-- Resumes here
- [ ] [P2-T3][direct] Implement session creation
```

No state file to parse. Just find first `[ ]` and continue.

## Consistency Check

On resume, validate:

- All tasks before the target should be `[x]` in plan
- If earlier tasks are unchecked, warn and ask user:
  - Keep them pending and skip for this run?
  - Go back and complete them?
  - Something else?

## Idempotent Task Execution

Tasks should be safe to re-execute:

| Task Type | Idempotent Approach |
|-----------|---------------------|
| Migration | Inspect the Drizzle journal and applied history; never recreate an applied migration |
| Schema | Compare the current schema and planned change before editing |
| Service/repository | Check existing methods and preserve unrelated behavior |
| React | Inspect the existing component or hook and retain platform-specific lifecycle behavior |
| Test | Reuse the nearest fixture and add only missing behavioral coverage |
| Route | Check route and schema registration before adding |

A repeated task must converge on the intended behavior without duplicating code or discarding concurrent edits. Verify current source before marking any task complete.

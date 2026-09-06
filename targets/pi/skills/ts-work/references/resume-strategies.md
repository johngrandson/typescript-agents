# Resume Strategies

## How State Works

**Plan checkboxes ARE the state.** No separate JSON state files.

- `[x]` = completed
- `[ ]` = pending; `[ ] ... [BLOCKED] ...` = blocked and still incomplete
- Phase status `[COMPLETED|IN_PROGRESS|PENDING|BLOCKED]` tracks phase progress
- `[BLOCKED]` on the plan row is authoritative; progress records preserve blocker evidence

## Resume Modes

### Default: Auto-detect

```
/skill:ts-work  # Resume at first unchecked non-[BLOCKED] task; stop if an earlier blocker exists
```

### From Specific Task

```
/skill:ts-work .claude/plans/session-creation/plan.md --from P2-T3
```

Targets P2-T3 regardless of earlier unchecked tasks. If it is `[BLOCKED]`, this explicitly retries it and clears the tag when starting.

### Skip Blockers

```
/skill:ts-work .claude/plans/session-creation/plan.md --skip-blockers
```

Skips rows visibly tagged `[BLOCKED]`; it does not infer blockers from prose or progress history.

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

No state file to parse. Select the first unchecked row not tagged `[BLOCKED]`, but stop when an unresolved blocker precedes it unless `--skip-blockers` was supplied.

## Consistency Check

On resume, validate:

- Tasks before the target must be `[x]`, or visibly `[BLOCKED]` when
  `--skip-blockers` was explicitly supplied
- If another earlier task is unchecked, warn and ask the user:
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

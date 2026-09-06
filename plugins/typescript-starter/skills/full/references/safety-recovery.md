# Safety Rails & Recovery

## Resume from Interruption

When resuming an interrupted workflow:

1. **Read progress file** `.claude/plans/{slug}/progress.md`
2. **Check plan checkboxes** in `.claude/plans/{slug}/plan.md`:
   - Count `[x]` (completed) vs `[ ]` (pending) tasks
   - Find the first unchecked task to resume from
3. **Validate artifacts**:
   - Ensure plan and progress files exist
   - Ensure completed tasks match checkboxes in plan
4. **Continue from first unchecked task**

Example resume:

```bash
/ts:full --resume session-revisions
# Reads .claude/plans/session-revisions/plan.md
# Finds first unchecked task: P2-T3
# Resumes from P2-T3
```

Or resume from specific task:

```bash
/ts:work .claude/plans/session-revisions/plan.md --from P2-T3
```

## Ralph Wiggum Integration

For fully autonomous execution, use with Ralph Wiggum Loop:

```bash
/ralph-loop:ralph-loop "/ts:full {feature}" --completion-promise "DONE" --max-iterations 50
```

This enables:

- Automatic recovery from context window limits
- Persistent execution across sessions
- The same bounded completion criteria and explicit INCOMPLETE outcome

## Automatic Stops

The cycle stops automatically when:

1. All tasks complete successfully
2. Max cycles reached
3. Max blockers reached
4. Fatal compilation error (unrecoverable)
5. Test suite completely broken (>50% failing)

## Human Checkpoints

Optional checkpoints for human review:

```
/ts:full {feature} --checkpoint-after plan
/ts:full {feature} --checkpoint-after each-phase
```

## Rollback Points

Verified commits and phase tags identify recovery points. Inspect `git status`, the checkpoint diff and ownership of affected files before reversing work. Preserve unrelated user/agent changes.

```bash
git status --short
git log --oneline
git diff <checkpoint>...HEAD
```

## Task-Level Checkpoints

When rollback is authorized, prepare a revert of the specific owned task commit as a reviewable diff, run the affected verification and commit the working reversal. Resolve
conflicts from the actual current tree. Do not reset --hard, force-move tags or rewrite shared history to resume a workflow.

Plan checkboxes and scratchpad must reflect the reverted task as pending, with reason and next action. Reconcile artifacts against Git evidence before continuing.

## State Recovery

Plan checkboxes ARE the state. If progress file is missing,
the plan still contains all state needed to resume:

```bash
# Check current progress from plan checkboxes
COMPLETED=$(grep -c '\[x\]' .claude/plans/${SLUG}/plan.md)
TOTAL=$(grep -c '\[.*\] \[P' .claude/plans/${SLUG}/plan.md)
echo "Progress: $COMPLETED / $TOTAL tasks complete"

# Resume from first unchecked task
/ts:work .claude/plans/${SLUG}/plan.md
```

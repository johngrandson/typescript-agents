# Error Recovery

## Verification Rules

Verification is tiered to balance speed and safety:

**Per-task** (after each task):

| Change Type | Verification Steps |
|-------------|-------------------|
| TypeScript source or tests (.ts/.tsx) | `pnpm --filter <workspace> lint` + `pnpm check-types` |
| Schema/migration | Above + `pnpm test:postgres` with disposable PostgreSQL |

**Per-phase** (after all tasks in a phase):

| Scope | Verification Steps |
|-------|-------------------|
| Always | `pnpm check-types` |
| Always | `pnpm --filter <workspace> test:run <affected_test_files>` |
| Always | `pnpm lint` |

**Final gate** (after all phases): `pnpm verify` (full type, lint, test and unused-code checks)

## When Verification Fails

1. **Compile error**: Read error, fix, retry
2. **Test failure**: Analyze failure, fix code or test
3. **Lint failure**: Inspect the workspace script; apply the configured formatter only to owned changes
4. **After 3 retries**: Mark the blocker in both plan and progress, write the scratchpad DEAD-END, and stop. Skip and continue only with explicit `--skip-blockers`

## BLOCKER Format

```markdown
## BLOCKER: P2-T3 — Task could not be completed

**Plan task**: `- [ ] [P2-T3][drizzle] [BLOCKED] Implement session creation`
**Task**: Implement session creation
**Attempts**: 3
**Last Error**: Test assertion failed - concurrent creation exceeded the configured session hard limit
**Files**: apps/api/src/modules/sessions/service.ts:45

**Action Required**: Human review needed
**Resume**: `/ts-work plan.md --from P2-T3`
```

**Also write a DEAD-END entry** to the scratchpad so future
sessions don't re-try the same failed approach:

```markdown
### [HH:MM] DEAD-END: {task description}
Tried: {approach attempted}. Failed because: {root cause}.
Attempts: 3. See BLOCKER in progress.md for full error.
```

Append to `.claude/plans/{slug}/scratchpad.md`.

By default, return control after recording this state. Only `--skip-blockers` may advance to a later task.

## Recovery After BLOCKER

When user resolves a blocker and resumes:

1. Re-read the plan file for current checkbox state
2. Start from the previously blocked task
3. Verify the fix compiles and tests pass
4. Mark checkbox and continue

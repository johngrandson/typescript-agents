# Harness Patterns for Error Recovery

Adapted from AutoHarness (Lou et al., 2026): programmatic verification
outperforms unstructured retry. A smaller model with good harnesses
beats a larger model without them.

## Critic-Refiner Pattern

When a task fails verification, use structured analysis instead of
immediate retry:

```
Attempt → Verify → FAIL
                    ↓
              Critic Phase (consolidate):
              - What EXACTLY failed? (first error only)
              - Is this the SAME error as before?
              - What has been tried already?
                    ↓
              Refiner Phase (targeted fix):
              - Address root cause from critic analysis
              - Don't repeat previous approaches
              - Check compound docs for known solutions
```

### When to Apply

- **Attempt 1**: Normal retry with error context
- **Attempt 2**: Pause. Compare errors. Same root cause = wrong mental model
- **Attempt 3**: Full critic analysis before BLOCKER decision

### Critic Analysis Template

Before the 3rd retry, consolidate:

```markdown
## Error Consolidation

**Command**: pnpm --filter @starter/api test:run src/modules/sessions/__tests__/service.test.ts
**Attempts**: 2 failed

**Error #1**: [exact error message]
**Error #2**: [exact error message]

**Same error?** Yes/No
- If YES → Root cause not addressed. Re-read source file.
- If NO → Progress made. New error is the real issue.

**Compound docs match?** grep -rl "KEYWORD" .claude/solutions/
**Dead-ends from scratchpad?** [any relevant entries]

**Next approach**: [specific, different from previous attempts]
```

## Action Verification Pattern

The plugin uses programmatic verification hooks (harness-as-action-verifier)
to surface suspicious changes after an edit. These hooks provide bounded checks, not proof of correctness:

| Hook | What It Verifies | Feedback On Failure |
|------|-----------------|---------------------|
| `format-typescript.sh` | Code formatting | "NEEDS FORMAT" warning |
| `iron-law-verifier.sh` | Iron Law violations in code content | Specific violation + line number |
| `security-reminder.sh` | Input, environment and implemented permission boundaries | Security review reminder |
| `error-critic.sh` | Repeated package-check failures | Consolidated error analysis |

Each hook follows the pattern:

1. **Propose** (Claude writes code)
2. **Verify** (hook checks programmatically)
3. **Report feedback** (specific warning or diagnostic via stderr)
4. **Retry** (Claude fixes the specific issue)

Use the reported file and line to inspect the actual change. Text matching can miss syntax and may flag harmless text; review each finding against source.
Missing tooling or unsupported runtime hooks must be reported explicitly. Continue with the configured type, lint and behavioral checks.

## Anti-Pattern: Unstructured Retry Loop

```
# BAD: Same approach, hope for different result
Attempt 1: pnpm test:run → FAIL
Attempt 2: tweak code → pnpm test:run → FAIL (same error)
Attempt 3: tweak more → pnpm test:run → FAIL (same error)
→ BLOCKER (wasted 3 attempts)
```

```
# GOOD: Critic-refiner with structured analysis
Attempt 1: pnpm test:run → FAIL
Attempt 2: compare errors → same root cause → re-read source
           → different fix approach → pnpm test:run → PASS
```

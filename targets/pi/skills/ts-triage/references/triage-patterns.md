# Triage Patterns

## Common Triage Decisions

### Always recommend fixing

Recommend fixing confirmed Iron Law violations and security issues.
Present the evidence and capture the user's decision; this list does not
authorize edits or silently choose the final severity.

- Untrusted interpolation into `sql.raw` or unsanitized content passed to
  React's `dangerouslySetInnerHTML`
- Missing required access checks at implemented identity boundaries
- Unvalidated input crossing a runtime boundary
- Binary floating-point arithmetic that violates a monetary precision or
  rounding requirement; choose integer minor units or a decimal contract
- Runtime database imports in browser code, bypassing the web Server
  Action/BFF boundary
- Non-idempotent Postgres job handlers or acknowledgements that bypass
  ownership-token and lease fencing
- `pnpm check-types` failures

### Usually Fix

Common TypeScript starter issues worth addressing:

- Confirmed N+1 SQL from repeated per-parent repository calls
- Drizzle query changes without Postgres/memory contract parity coverage
- Large React lists with measured render costs and no pagination or
  virtualization where needed
- Subscriptions or timers retained after cleanup
- Job payload changes without shared runtime validation or compatibility
  handling for already queued JSON
- Tests without assertions or using arbitrary timer sleeps
- Missing error handling on external API calls

### Often Skip

Low-impact or cosmetic issues:

- Optional style preferences when the configured ESLint and formatting
  checks already pass
- Extra documentation on self-explanatory internal modules
- Cosmetic naming improvements
- Rewriting readable early returns as nested branches without a behavior change
- Redundant type annotations on local functions when inference and lint
  checks already establish the intended contract

### Context-Dependent

Ask the user for these — the right answer depends on project
stage and priorities:

- Performance optimizations (premature vs. needed)
- Test coverage for edge cases (shipping deadline?)
- Refactoring suggestions (tech debt budget?)
- Documentation improvements (internal vs. public API?)

## Severity Reclassification Guide

### Downgrade from BLOCKER when

- The issue is in code that's not yet reachable
- There's an existing workaround in production
- The fix requires a separate migration/PR
- The issue existed before this change (pre-existing)

### Upgrade from SUGGESTION when

- The pattern will be copied by future developers
- It affects a security-sensitive code path
- It causes confusion in code review
- It violates an Iron Law

## Triage Anti-Patterns

### "Fix everything" without thinking

If you approve every finding, you didn't need triage. Either
skip triage and go straight to `/skill:ts-plan`, or be more
selective about what's worth fixing now.

### "Skip everything" to ship faster

If you skip more than 70% of findings, the review wasn't
useful or you're cutting too many corners. At minimum, fix
all BLOCKERs and most WARNINGs.

### Triaging without reading

Each finding deserves 10-30 seconds of thought. If you're
pattern-matching on severity alone, you're missing context.

## Batch Triage for Large Reviews

When a review has 15+ findings:

1. First pass: Recommend all confirmed BLOCKERs for fixing and capture the decision
2. Second pass: Present WARNINGs for decision
3. Third pass: Batch SUGGESTIONs — "Skip all suggestions?"

This prevents decision fatigue on large reviews.

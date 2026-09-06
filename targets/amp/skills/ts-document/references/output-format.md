# Documentation output format

Write the report to `.claude/plans/{slug}/reviews/{feature}-docs.md`.
Use this structure, retain only sections actually completed, and record observed
verification results. The symbols below exist in the starter; the table does
not claim that this documentation work has already been performed.

```markdown
# Documentation: {Feature}

## Updated declarations

| Symbol | Source | Documented behavior |
| --- | --- | --- |
| `SessionService` | `apps/api/src/modules/sessions/service.ts` | Domain mutations and post-write events |
| `SessionRepository` | `packages/db/src/repository.ts` | Missing records, revision metadata and atomic writes |

## Public API details

| Method | Behavior to explain |
| --- | --- |
| `SessionService.update(sessionId, patch)` | Omitted fields, missing sessions and the resulting event |
| `SessionRepository.findRevisionedById(sessionId)` | Snapshot and revision, or null for a missing session |

## User-facing documentation

- README section: {actual section and changed behavior}
- ADR: {actual path, tested decision and consequences, if created}

## Verification

- Source and tests inspected: {exact paths}
- Command: {command actually executed}
- Result: {exit status, assertions and remaining coverage gaps}

## Checklist

- [ ] JSDoc explains invariants and side effects of changed exported declarations
- [ ] Examples match tested TypeScript code and actual response envelopes
- [ ] README reflects changed user-facing behavior
- [ ] Consequential decisions have an ADR when warranted
```

---
name: ts-trace
description: Use when tracing a TypeScript symbol from API routes, web actions/hooks,
  mobile services/screens…
---

# Call tracing

## Usage

```text
$typescript-starter:ts-trace SessionService.update
rg -n "SessionService|applySessionEvent" apps packages/types/src
```

## Procedure

1. Locate the symbol declaration, exports, aliases and direct callers with rg and source inspection. Follow imports and package exports; static text hits alone are not proven calls.
2. Recurse toward entry points, tracking visited file/symbol pairs and limiting depth to 10. Record unresolved dynamic/callback edges and cycles rather than looping or inventing callers.
3. Extract input transformations, shared DTOs, error/async boundaries and effects. Stop at Fastify routes/SSE/WS admission, web Server Actions/UI hooks, mobile screens/REST/WS
   services and worker registry handlers.
4. For broad traces, optional native generic workers may inspect independent entry-point categories. The same-session sequential path is fully supported and must produce the same call tree. Never
   require a named custom agent. Wait for every selected category, preserve coverage gaps and reconcile evidence in this session.

## Starter example

Trace `SessionService.update` through Fastify PATCH validation, repository mutation and post-write broadcast. Then trace web `updateSession` Server Action and mobile ApiService
separately. `applySessionEvent` is the shared client projection. Worker repository use does not imply an API service import.

## Output

Write `.claude/plans/{slug}/research/call-tree-{symbol}.md` with tree/graph, entry-point table, arguments at each edge, conditions, evidence and affected verification targets. Knip
detects unused imports/exports; it cannot establish the entire call tree.

## Iron Laws

1. Confirm import/call edges in source; text matches alone are only candidates.
2. Track visited file/symbol pairs, stop at real entry points and cap recursion at depth 10.
3. NEVER invent dynamic callers or silently omit a missing tracing category.

## References

- [Argument extraction](references/argument-extraction.md)
- [Entry points](references/entry-points.md)
- [Import call analysis](references/import-call-analysis.md)

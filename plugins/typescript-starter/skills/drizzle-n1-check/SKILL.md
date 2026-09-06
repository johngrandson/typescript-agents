---
name: drizzle-n1-check
description: Use when N+1 queries are suspected in repository calls inside loops or repeated SQL per parent record; not for unrelated database performance.
effort: medium
allowed-tools: Read, Grep, Glob, Bash
---

# N+1 detection

## Usage

```text
rg -n "findById|Promise.all" apps/api/src packages/db/src
pnpm --filter @starter/db test:run
pnpm test:postgres
```

## Evidence first

Read repository consumers and adapters together. Search loops with `rg -n 'for \(|\.map\(|Promise\.all|findById' apps packages/db/src`. A loop is a candidate, not proof:
`SessionService.list()` maps in-memory participant counts from the event bus and must not be reported as N+1 SQL.

Capture query count for a bounded fixture at two parent cardinalities. A query count growing once per parent supports N+1; inspect emitted SQL and call sites to establish the
cause. Never fabricate query counts from static matching.

## Remedy

Prefer an existing list/batch repository operation, join, aggregate or bounded query with `inArray` when semantics permit. Return only needed projections and preserve
ordering/nullability. Add port and memory behavior when introducing a batch method. Drizzle does not automatically lazy-load an association when a DTO property is accessed.

Check that a join does not multiply parent rows, change pagination or omit parents without children. Compare both SQL count and returned data. Use `EXPLAIN` on safe queries when
needed; `EXPLAIN ANALYZE` executes its statement, so writes require a disposable database.

## Output

Provide candidate path, observed SQL/count growth, affected operation, proposed query shape and parity/regression evidence. If instrumentation is unavailable, report an unconfirmed
candidate. Use `/ts:perf` for broader latency/index work.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

## References

- [Batch patterns](references/batch-patterns.md)
- [Query optimization](references/query-optimization.md)

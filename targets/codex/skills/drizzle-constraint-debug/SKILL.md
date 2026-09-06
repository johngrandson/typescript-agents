---
name: drizzle-constraint-debug
description: Use when a Postgres SQLSTATE or named unique, foreign-key, check, or
  not-null constraint fails…
---

# Drizzle constraint debugging

## Usage

```text
pnpm --filter @starter/db test:run src/__tests__/errors.test.ts
pnpm test:postgres
```

## Procedure

1. Capture the operation and SQLSTATE without logging bound values. `DrizzleQueryError` may wrap a driver cause. `packages/db/src/errors.ts` preserves only a validated
   five-character code in safe messages.
2. Identify the constraint in `packages/db/src/schema.ts` and generated SQL under `packages/db/drizzle`. Confirm the migration actually applied to the database being queried.
3. Trace every repository write path, including worker and retention jobs. Read input TypeBox schemas separately; they cannot establish concurrent uniqueness.
4. Reproduce using a disposable Postgres fixture. Test the same repository method in memory to identify adapter drift.
5. Classify: 23505 unique, 23503 foreign key, 23514 check, 23502 not-null. Missing migrations and stale data need different remedies from racing requests.
6. Fix the invariant, query or migration. For concurrent admission/ordering/revisions, assert atomic behavior under simultaneous calls. Never reset a database or delete conflicting
   data to silence the failure.

## Output

Report constraint and SQLSTATE, migration status, call path, minimal reproduction, root cause and a verified fix. Mark schema or database visibility gaps explicitly. Parameterized
diagnostic queries should use a bounded result set and a confirmed disposable/read-only target.

## Starter example

This excerpt uses the existing implementation; read its source for imports and setup.

Source: `packages/db/src/errors.ts`.

```typescript
export function databaseErrorMessage(error: unknown): string | undefined {
  if (!(error instanceof DrizzleQueryError)) return undefined;

  const cause = error.cause;
  const code = cause && 'code' in cause ? cause.code : undefined;
  return typeof code === 'string' &&
    code.length === 5 &&
    /^[0-9A-Z]{5}$/.test(code)
    ? `Database query failed (SQLSTATE ${code})`
    : 'Database query failed';
}
```

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

## References

- [Constraint patterns](references/constraint-patterns.md)

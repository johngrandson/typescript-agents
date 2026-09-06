---
name: drizzle-patterns
description: Use when editing Drizzle schemas, SQL queries, transactions, migrations,
  indexes, repository…
---

# Drizzle persistence

Storage belongs in `packages/db`. Read `schema.ts`, `repository.ts`, the Drizzle adapter, the memory adapter and relevant shared contract tests together.

## Usage

```text
pnpm --filter @starter/db check-types
pnpm --filter @starter/db test:run
pnpm test:postgres
```

## Iron Laws

1. TypeBox in `packages/types` owns boundary schemas and derived DTOs. Drizzle owns tables, constraints, transactions and projections. Do not duplicate input validation in hand-written client types.
2. Preserve the Postgres/memory repository contract, including nullability, complete snapshots, order, timestamps and revision metadata. Memory-only success does not verify SQL behavior.
3. Use parameterized Drizzle expressions; never interpolate untrusted identifiers or values into raw SQL. Bound SQL diagnostic output can contain secrets.
4. Keep atomic operations inside one transaction. Read/update/revision metadata must describe the same successful write. A count-before-create outside the transaction cannot enforce
   concurrent admission limits.
5. Generate migrations using the installed Drizzle CLI through `pnpm db:generate`; inspect SQL and metadata in `packages/db/drizzle`. Apply to a disposable database first. Never
   rewrite an applied migration or reset a database to hide drift.
6. Inspect actual query count and plans before optimizing. Missing joins, unbounded projections and calls in loops have different remedies.

## Verification sequence

Run `pnpm --filter @starter/db check-types`, `pnpm --filter @starter/db test:run` and, when SQL changes, `pnpm test:postgres`. The Postgres suite uses disposable infrastructure;
record unavailable infrastructure as BLOCKED or NOT RUN, not a pass. Verify migration from the previous schema and parity of both adapters. Review `pnpm db:push` separately because
it mutates schema without the reviewed migration path.

The custom job repository uses ownership tokens and lease deadlines. Changes to `claim`, `renew`, `complete`, `fail` or `abandon` must preserve fencing and at-least-once execution.

## Starter example

This excerpt uses the existing implementation; read its source for imports and setup.

Source: `packages/types/src/schemas/common.ts`.

```typescript
export const DetailOf = <T extends TSchema>(schema: T) =>
  ObjectType({ data: schema });

/** List totals retain the existing numeric wire contract. */
export const ListOf = <T extends TSchema>(schema: T) =>
  ObjectType({
    data: ArrayType(schema),
    total: Integer({ minimum: 0 }),
  });
```

## References

- [Input contracts](references/input-contracts.md)
- [Fulltext search](references/fulltext-search.md)
- [Migrations](references/migrations.md)
- [Queries](references/queries.md)
- [Transactions](references/transactions.md)

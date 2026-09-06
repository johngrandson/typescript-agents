# Measure query growth

Compare bounded fixtures with different parent counts and record emitted SQL. Calls inside loops are candidates; in-memory projection or bus.getConnectionCount does not establish
N+1. Do not invent counts from a static search.

Choose batching, joins or aggregates based on the returned contract, then compare query count and data parity. EXPLAIN ANALYZE executes a query; only use mutating variants against
disposable infrastructure.

## Starter evidence

Read `packages/db/src/drizzle-repository.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

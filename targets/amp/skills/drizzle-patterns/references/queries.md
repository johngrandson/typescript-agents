# Query composition and projections

Read the query needed by the repository port before selecting SQL shape. List uses SessionSummary; detail returns complete SessionSnapshot. Parameterize values and preserve stable
ordering and parent rows without items.

A join can multiply rows and break pagination. Confirm returned data as well as query count. Extend the port and memory adapter together if a new batch operation is needed; do not
leak a Drizzle query object to routes.

## Starter evidence

Read `packages/db/src/drizzle-repository.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

# Search design when requested

The starter does not install a full-text search feature. Inspect actual searchable columns and query consumers before choosing a Postgres expression, index or dedicated service. Do
not present a search migration as existing code.

Define matching/ranking, pagination, language and update requirements. Prototype SQL on disposable data and measure its plan at realistic size. Parameterize terms, retain rows
according to the specified semantics, and test both repository adapters if search becomes a port operation.

## Starter evidence

Read `packages/db/src/schema.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

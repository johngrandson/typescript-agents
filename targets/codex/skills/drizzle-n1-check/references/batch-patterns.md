# Batch related data

Drizzle DTO access has no implicit association lazy loading. Related data must be queried explicitly. An existing list/detail operation may already fetch the needed projection;
inspect it before adding a batch method.

If batching is required, preserve parent ordering, empty-child behavior and pagination. Implement the corresponding memory port behavior and test duplicate IDs and missing records.
Avoid replacing one N+1 with an unbounded join.

## Starter evidence

Read `packages/db/src/repository.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

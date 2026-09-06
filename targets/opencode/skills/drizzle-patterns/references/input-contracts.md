# Input contracts and persistence

TypeBox schemas define runtime input/output; Static derives TypeScript DTOs. Read schema exports and validator entry points before adding fields. Omitted patch fields must remain
omitted rather than becoming null or defaults.

Database constraints protect persisted invariants and concurrency; HTTP validation has a different job. Test API normalization and Postgres constraints separately. Update every DTO
projection and both adapters when schema fields change.

## Starter evidence

Read `packages/types/src/schemas/session.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

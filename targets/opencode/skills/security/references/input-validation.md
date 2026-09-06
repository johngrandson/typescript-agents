# Validate every boundary

Use shared TypeBox schemas and validators for HTTP inputs/responses, socket events and documents. Static types do not validate JSON. Read Fastify schema options to know whether
extra fields are removed, coerced or rejected.

Test malformed, missing, oversized and unexpected fields; preserve canonical errors. Keep validation separate from authorization and storage invariants.

## Starter evidence

Read `packages/types/src/validators/index.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

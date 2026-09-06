# Strict static types

DTOs use `Static<typeof Schema>` rather than duplicated interfaces. Discriminated event unions and satisfies expose impossible combinations at compile time. Treat unknown from the
network as unvalidated until the validator succeeds.

Typechecking verifies assignments, not deployed runtime behavior. Test schema/DTO parity, invalid inputs and package entry points. Do not convert compiler warnings from another
language into TypeScript rules.

## Starter evidence

Read `packages/types/src/session.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

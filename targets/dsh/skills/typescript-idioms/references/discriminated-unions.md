# Discriminated unions

Switch on the SessionEvent type and preserve the shared pure projection. Check session identity before applying an event and keep ordering/idempotence behavior consistent between clients.

Use narrowing rather than unsafe casts. Add a case and projection tests when an event is introduced; update runtime schemas and both transport validators in the same change.

## Starter evidence

Read `packages/types/src/session-projection.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

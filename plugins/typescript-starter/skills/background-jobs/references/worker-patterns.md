# Handler design

A handler has kind, description and handle(payload, ctx). Validate untrusted payloads and check AbortSignal around effects. Use JobContext repositories and enqueue; never import
API modules or its in-memory event bus.

Archive publication is immutable per job identity and validates already-published data. Test duplicate attempts, malformed payload, missing session and conflicting documents.
At-least-once delivery requires idempotent external effects.

## Starter evidence

Read `apps/worker/src/handlers/archive-session.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed
source hashes before adapting them.

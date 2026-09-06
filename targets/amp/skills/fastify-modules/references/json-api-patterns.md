# API envelopes

List responses carry data plus total; detail responses carry data only; deletion sends a bodyless 204. AppError maps domain codes to HTTP status and the canonical error envelope.
Unknown errors are sanitized by deployment policy.

Use shared response schemas from packages/types and validate consumers. Do not claim a TypeScript response cast checks runtime data. Test missing, malformed, conflict and INTERNAL
cases without exposing SQL or bound values.

## Starter evidence

Read `apps/api/src/core/errors.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

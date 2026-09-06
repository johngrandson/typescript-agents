# HTTP and proxy security

Read actual Fastify CORS registration, error handling and web proxy behavior. Document observed headers separately from proposed controls. Public env values, API origins and
credentials must stay within their intended trust boundaries.

Test allowed/disallowed origins according to the real deployment policy. A response header is not identity. Preserve SSE streaming/cache behavior and cancellation while changing proxies or headers.

## Starter evidence

Read `apps/api/src/app.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

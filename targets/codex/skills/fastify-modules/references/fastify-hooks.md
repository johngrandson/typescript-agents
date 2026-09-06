# Fastify lifecycle hooks

Read registration order, onClose hooks, validation and error handling in buildApp. Use typed Fastify plugin factories and explicit register calls. An import must not start
listeners, timers or a global registry.

Keep request-scoped behavior in Fastify hooks and app-scoped resources in the composition root. Verify malformed payloads, readiness and repeated shutdown using app.inject and
lifecycle tests. A plugin hidden from /modules still mounts; hidden is not authorization.

## Starter evidence

Read `apps/api/src/app.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

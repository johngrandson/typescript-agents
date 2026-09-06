# Authentication boundary

The current API is unauthenticated. UUID path validation and random stream client IDs do not validate credentials. Never describe an actor/session auth framework as installed.

For a protected feature, first define credential transport, verification, expiry/revocation and identity propagation. Check REST, SSE and WS upgrade/subscription separately. Keep
secret material out of logs and public env variables.

## Starter evidence

Read `apps/api/src/modules/sessions/routes.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

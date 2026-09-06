# Identity and operation scope

The starter does not authenticate an actor. Its randomUUID clientId identifies a stream connection. Session IDs and UUID schemas are not permission checks. Treat protected-user
features as a new boundary to design explicitly.

If identity is added, validate credentials before REST/SSE/WS access and pass domain identity deliberately into service decisions. Test cross-owner reads, writes and subscriptions.
Do not paste an authorization library API as if already installed.

## Starter evidence

Read `apps/api/src/modules/sessions/routes.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

# Authorization boundary

Services currently enforce domain existence and limits, not actor ownership. Do not infer authorization from notFound, hidden UI or knowing a session ID.

When identity exists, define operation permissions at the service boundary and validate access before subscription. Test cross-owner reads/writes and permission changes. Report
missing authorization as a scoped requirement gap rather than inventing an existing policy engine.

## Starter evidence

Read `apps/api/src/modules/sessions/service.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

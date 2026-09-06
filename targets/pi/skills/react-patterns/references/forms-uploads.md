# Forms and mutations

Web mutations call Server Actions, which use the server-only API client and established action-result mapping. Preserve transitions and error presentation. Mobile uses REST
services and screen hooks; it cannot call a Next Server Action.

Read existing storage routes before promising an upload feature: JSON document storage does not imply arbitrary multipart uploads. Validate any new payload through shared schemas
and test pending, failure, retry and stale-response behavior.

## Starter evidence

Read `apps/web/app/actions/actions.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

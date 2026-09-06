# Identity linking is not installed

There is no OAuth/account-linking implementation in the starter. A connection clientId cannot serve as user identity, and an email field would not prove ownership. Specify
identity-provider trust and account association as new requirements if requested.

A future linking flow must verify the current credential and the new provider identity, handle collisions deliberately and test cross-account attacks. Do not introduce speculative
APIs or credentials to make an example run.

## Starter evidence

Read `apps/api/src/modules/sessions/routes.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

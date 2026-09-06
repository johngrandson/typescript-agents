---
name: security
description: Use when reviewing input validation, SQL injection, error exposure, storage
  paths, stream…
---

# Starter security

The current starter has no installed authentication or authorization system. `clientId` is a random connection identifier, not authenticated identity. Never claim CORS, UUID
validation, hidden UI or knowledge of an object ID grants authorization.

## Usage

```text
pnpm --filter @starter/api test:run src/core/__tests__/httpErrors.test.ts
pnpm --filter @starter/db test:run src/__tests__/document-store.test.ts
```

## Existing boundaries

1. Validate params, payloads, responses and events using shared TypeBox schemas/validators in `packages/types`. Validate REST, SSE, WS and persisted documents, not only browser
   forms. Inspect actual Fastify coercion/removal behavior before describing strictness.
2. Parameterize Drizzle SQL. Do not expose SQL text, bound values, raw driver errors or secrets in responses and logs; use `databaseErrorMessage` at existing logging boundaries.
3. Return API errors through `toErrorResponse`. Preserve expected `AppError` codes; deployed unknown failures get a generic INTERNAL message. Do not hide domain failures under a
   blanket successful response.
4. Keep private environment access in `packages/env` and server-only modules. Public Next/Expo settings are visible to clients. Avoid logging tokens or full payloads.
5. Constrain storage filenames, directories and document shapes using `createJsonDocumentStore`; test traversal, malformed documents, conflicts and permission failures.
6. Preserve HTTP body limits, request/stream deadlines, subscription cleanup and retention/admission controls. Confirm actual rate-limiting implementation; do not imply a quota
   layer exists because admission returns 429.

## When identity is requested

Design the actor, credential validation, ownership rules and permission checks before treating operations as protected. Test unauthenticated requests and cross-owner access at
REST, SSE and WS boundaries once that feature exists. CSRF defense depends on the credential transport and deployment; SameSite/CORS alone must not be asserted sufficient for an
unspecified auth design.

Report concrete paths, exploit prerequisites, affected data and regression evidence. Review source without performing destructive probes against a live service.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

## References

- [Advanced patterns](references/advanced-patterns.md)
- [Authentication](references/authentication.md)
- [Authorization](references/authorization.md)
- [Input validation](references/input-validation.md)
- [Oauth linking](references/oauth-linking.md)
- [Rate limiting](references/rate-limiting.md)
- [Security headers](references/security-headers.md)

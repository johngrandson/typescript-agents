---
name: fastify-modules
description: Use when editing Fastify routes, services, module registration, AppContext
  composition, error envelopes, or API module boundaries.
---

# Fastify modules and services

Follow `apps/api/src/modules/sessions`: `schemas.ts` exposes shared contracts, `routes.ts` validates/delegates/wraps, and `service.ts` owns domain rules in `SessionService`.
`AppContext` assembles repositories, the per-app event bus and limits once.

## Usage

```text
pnpm --filter @starter/api test:run src/modules/sessions/__tests__/routes.test.ts
```

## Iron Laws

- Keep service methods callable with primitives and DTOs; a service must not require an HTTP request/reply. Constructor injection through `AppContext` is intentional.
- Use the repository port for storage. Postgres and memory implement the same observable contract. Do not discourage service objects or repository interfaces.
- Add modules through the explicit registry in `apps/api/src/plugins/registry.ts`. Imports should not start listeners or scan the filesystem to auto-register routes.
- Validate shared input and response TypeBox schemas. List responses carry `{ data, total }`; detail responses carry `{ data }`. Do not add `total` to details or JSON to 204 responses.
- Map expected failures through `AppError` and `toErrorResponse`; preserve unknown internal errors as server failures. Log database errors through `databaseErrorMessage` without exposing SQL values.
- Broadcast after a successful mutation using the repository's revision metadata. The in-memory event bus is scoped to an API instance, not a distributed transport.
- Keep the worker independent of API imports. Share contracts and repository capabilities through packages; extract reusable domain code deliberately when needed.

## Boundaries

Split a module when it owns a different invariant or lifecycle, not to satisfy a lines-per-file target. Route factories may be reused when contracts and policies really match
(`storageRoutes` is an existing example). Read all consumers before changing an exported contract. The starter has no authenticated actor; random socket IDs and CORS are not
authorization.

## Verification

Use service tests for invariants, Fastify `app.inject()` tests for HTTP schemas/envelopes, registry tests for registration, and repository contract tests for storage behavior. An
isolated app has its own context and must close its resources.

```typescript
    app.post(
      '/sessions',
      {
        schema: {
          summary: 'Create a session.',
          tags: ['sessions'],
          body: CreateSessionSchema,
          response: { 201: SessionDetailSchema, 429: ErrorResponseSchema },
        },
      },
      async (request, reply) =>
        reply.code(201).send({ data: await service.create(request.body) }),
    );
```

Source: `apps/api/src/modules/sessions/routes.ts`.

## Apply the reference

1. Read SessionService and the shared request/response schemas for the operation being changed.
2. Register the route factory through the module registry and pass its AppContext explicitly.
3. Run the service invariant tests and Fastify injection tests for the changed HTTP boundary.
4. Verify response envelopes, error classification and cleanup with the existing isolated app fixtures.

## References

- [Context patterns](references/context-patterns.md)
- [Json api patterns](references/json-api-patterns.md)
- [Fastify hooks](references/fastify-hooks.md)
- [Routing patterns](references/routing-patterns.md)
- [Identity boundaries](references/identity-boundaries.md)

NEVER treat an unexecuted check as a pass or use an unverified framework assumption to justify a change.

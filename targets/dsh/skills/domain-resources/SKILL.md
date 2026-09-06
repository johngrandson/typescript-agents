---
name: domain-resources
description: Use when designing a domain operation across shared TypeBox contracts,
  Fastify services, Drizzle repositories, effects, and clients.
---

# Domain operations

Treat Session as the reference vertical slice. There is no resource framework or installed identity/authorization system in this starter.

## Usage

```text
pnpm --filter @starter/types test:run
pnpm --filter @starter/api test:run src/modules/sessions/__tests__/service.test.ts
```

## Design sequence

1. Define the operation and invariants: input, success envelope, missing/conflict outcomes and effects. Read `packages/types/src/schemas`, derive DTOs with `Static`, and export
   through the existing contract entry points. Keep projections pure.
2. Add persistence needs to the port in `packages/db/src/repository.ts`; implement both Postgres and memory adapters. Run the same repository contract suite for each. Validate
   race-sensitive constraints inside the transaction, not just at an HTTP boundary.
3. Place domain decisions in a service. `SessionService` receives `AppContext`; its methods take domain values rather than Fastify requests. Methods return complete DTOs or throw `AppError`.
4. Register a thin module via `apps/api/src/plugins/registry.ts`. Its `routes.ts` validates TypeBox params/body and chooses an existing response envelope: `{ data }`, `{ data,
   total }`, error, or bodyless 204.
5. Publish API events only after the successful repository write. The API event bus belongs to one app instance; the worker cannot access it. Shared revision metadata and
   `applySessionEvent` must remain consistent across clients.
6. Wire web mutations through Server Actions, mobile mutations through REST services. Test contract validation, service decisions, repository parity and both transports separately.

## Decisions and limits

Services and repository interfaces are intended architecture. Do not replace them with global database imports in handlers. An ID or socket `clientId` is not authenticated
identity. If a requested feature needs authorization, specify the missing identity boundary and policies explicitly; do not claim it already exists. Adding an authorization
framework, new queue or distributed event system requires a real requirement.

For the existing creation invariant inspect `createIfBelowLimit`: concurrent requests must not both pass an application-only count check. The returned mutation includes revision
metadata from the same successful write. Design schema, service and query responsibilities separately; route validation cannot replace a database constraint.

## Starter example

This excerpt uses the existing implementation; read its source for imports and setup.

Source: `packages/types/src/session.ts`.

```typescript
export type CreateSessionInput = Static<typeof CreateSessionSchema>;

/** Partial by design: only the fields actually sent are applied. */
```

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

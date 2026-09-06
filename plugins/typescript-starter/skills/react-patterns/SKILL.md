---
name: react-patterns
description: Use when editing Next.js React or Expo/React Native UI, forms, state, navigation, subscriptions, SSE/WS recovery, or shared event projection.
effort: medium
user-invocable: false
paths:
- apps/web/**/*.tsx
- apps/web/**/*.ts
- apps/mobile/src/**/*.tsx
- apps/mobile/src/**/*.ts
- packages/ui/**/*.tsx
---

# React web and mobile

Read the target workspace before choosing a recipe. Web and mobile share contracts and projection functions; their rendering and mutation paths differ.

## Usage

```text
pnpm --filter @starter/web test:run
pnpm --filter @starter/mobile test:run
```

## Web: Next.js App Router

Use Server Components for initial server reads and Server Actions in `apps/web/app/actions/actions.ts` for mutations through `lib/api-client.ts`. Client components hold interaction
state and use the established action-result/transition patterns. Do not replace this with `useState + useEffect + fetch` for initial server data. `packages/ui` components use DOM
and Tailwind tokens.

SSE reaches the browser through `apps/web/app/api/sessions/[sessionId]/events/route.ts`, the BFF proxy. Preserve stream cancellation, deadlines, response validation and recovery
behavior in the session event hook. Never import `server-only` API code into a Client Component.

## Mobile: Expo and React Native

Use React Navigation, native components, `apiService.ts` for REST and `websocketService.ts` for WS. Screen loading hooks and Zustand stores are existing patterns; do not apply the
web restriction to legitimate mobile loading effects. Cancel stale loads, gate updates by request ownership and release subscriptions on navigation/unmount. DOM components from
`packages/ui` cannot render as native components.

## Shared realtime contract

Both clients validate incoming events and use `applySessionEvent` from `packages/types`. Keep the pure projection shared, preserve session IDs, revisions, idempotent item additions
and reconnect/resync semantics. A socket `clientId` identifies a connection, not a signed-in user. The API event bus is local to an app instance; do not promise cross-instance
delivery.

## Verification

Test projection independently, then test web actions/SSE and mobile REST/WS adapters. Testing Library checks UI interactions; Playwright covers browser flows. Those checks do not
establish native device rendering. Record Android/iOS export or device coverage separately.

## Starter example

This excerpt uses the existing implementation; read its source for imports and setup.

Source: `apps/web/app/actions/actions.ts`.

```typescript
export async function updateSession(
  sessionId: SessionId,
  input: UpdateSessionInput,
): Promise<ActionResult<SessionSnapshot>> {
  return runMutation(
    () => client().updateSession(sessionId, input),
    `/sessions/${sessionId}`,
  );
}
```

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

## References

- [Async streams](references/async-streams.md)
- [Participants transports](references/participants-transports.md)
- [Components](references/components.md)
- [Forms uploads](references/forms-uploads.md)
- [Js interop](references/js-interop.md)
- [Projection navigation](references/projection-navigation.md)

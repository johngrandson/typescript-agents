---
name: typescript-idioms
description: Use when designing strict TypeScript modules, schemas, async control flow, unknown errors, Node lifecycle, or imports across Fastify/React workspaces.
effort: medium
user-invocable: false
---

# TypeScript and Node idioms

Use the workspace's existing TypeScript configuration, package exports and runtime. Node is the server runtime. pnpm/Turborepo order builds; application entrypoints own process startup and shutdown.

## Decisions

- Model boundary data with TypeBox and derive types using `Static`. Use discriminated unions, `satisfies`, and exhaustive switches when they preserve the contract. A cast is not runtime validation.
- Use `import type` for types. `packages/types` has explicit `.js` relative imports for emitted ESM and separate `/schemas` and `/validators` entries. `packages/ui` exports source
  for the bundler; do not impose one import style on all workspaces.
- Await work whose completion owns a resource. Use `Promise.all` only for independent operations; preserve order when transactions, ownership or cleanup depend on it. Limit concurrency explicitly.
- Catch `unknown`, classify the specific expected error and rethrow others. Keep API error envelopes separate from storage errors and worker retry decisions.
- Start timers and servers explicitly, capture handles, and dispose them in shutdown. Use `AbortSignal` for cooperative cancellation. A timeout does not prove detached I/O has stopped.
- Prefer injected instances over module-level mutable singletons. API tests create independent contexts; worker shutdown awaits active work before storage closes.

## Process boundary

Requests share the Node process heap. Blocking synchronous work blocks its event loop. Avoid unbounded retained state, concurrent timer ticks,
floating promises and swallowed shutdown errors. Inspect `apps/api/src/core/lifecycle.ts` and `apps/worker/src/runner.ts` for real lifecycle contracts.

## Verification

Run each affected package's `check-types`, `lint` and `test:run` scripts. Test cancellation, repeated start/stop and two independent instances where relevant. A successful
typecheck does not validate data arriving from HTTP, disk or sockets.

## Starter example

This excerpt uses the existing implementation; read its source for imports and setup.

Source: `packages/types/src/session-projection.ts`.

```typescript
function dedupeParticipants(
  participants: SessionParticipant[],
): SessionParticipant[] {
  const seen = new Map<string, SessionParticipant>();
  for (const participant of participants) {
    seen.set(participant.clientId, participant);
  }
  return [...seen.values()];
}
```

## Iron Laws

1. Use TypeBox runtime validation before narrowing external data to a DTO.
2. NEVER let a type cast hide unknown input, an unhandled error or an invalid package export.
3. Await owned async work and verify resource cleanup before declaring a lifecycle safe.

## References

- [Anti patterns](references/anti-patterns.md)
- [Version compatibility](references/version-compatibility.md)
- [Strict types](references/strict-types.md)
- [Error handling](references/error-handling.md)
- [Pnpm tasks](references/pnpm-tasks.md)
- [Node lifecycle](references/node-lifecycle.md)
- [Discriminated unions](references/discriminated-unions.md)
- [Troubleshooting](references/troubleshooting.md)
- [Async composition](references/async-composition.md)

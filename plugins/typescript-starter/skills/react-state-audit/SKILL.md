---
name: react-state-audit
description: Use when React or React Native retains stale state, duplicate snapshots, unbounded lists, listeners, sockets, or timers after navigation.
effort: medium
argument-hint: path/to/component-or-hook.tsx
allowed-tools: Read, Grep, Glob, Bash
---

# React state retention audit

Audit a specific component, hook, store or navigation path. Read both writers and readers of retained data.

1. Inventory state ownership: server snapshot, local form state, Zustand selection, event projection and derived values. Flag duplicated sources only when they can drift; local
   editable state has a different purpose from the server snapshot.
2. Trace subscription creation and cleanup in web SSE hooks and mobile WS services. Check repeated mount/unmount, reconnect, session switch and cancellation while a load is pending.
3. Inspect request ownership: an old REST response must not overwrite a newer selected session. Check revisions and resync behavior before applying events.
4. Check bounded lists, retained closures, timer handles and listeners. Use profiling/heap snapshots when available; source alone cannot establish memory in bytes.
5. Verify store updates preserve intended selectors and reset policy. Do not replace legitimate mobile loading hooks with server-only Next patterns or use DOM components in native screens.

## Usage

```text
/ts:react-state-audit apps/mobile/src/screens/SessionDetail/useSessionDetail.ts
pnpm --filter @starter/mobile test:run src/screens/SessionDetail/__tests__/loadOwnership.test.ts
```

## Evidence and output

Use `apps/web/components/session-panel/hooks/use-session-events.ts`, `apps/mobile/src/screens/SessionDetail`, `apps/mobile/src/store` and `packages/types/src/session-projection.ts`
as references. Report owner, lifetime, retained value, reproduction, measured evidence and cleanup fix. Test repeated navigation and stale requests; report runtime profiling as NOT
RUN if unavailable. Avoid invented per-component memory estimates.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. NEVER bypass tests or reset a database to obtain a passing result.

---
name: testing
description: Use when writing or repairing Vitest, Fastify inject, repository contract, Testing Library, Playwright, or asynchronous lifecycle tests.
effort: medium
user-invocable: false
paths:
- '**/__tests__/**/*.ts'
- '**/__tests__/**/*.tsx'
- '**/*.test.ts'
- '**/*.test.tsx'
- apps/e2e/**/*
---

# Testing the starter

For web and mobile, choose the smallest existing suite that observes the behavior, then cover the boundaries the change crosses. Run installed package scripts; do not bypass gates
or disable failing tests.

| Layer | Existing technique | What it establishes |
| --- | --- | --- |
| Contracts | Vitest schemas, validators and projection tests | Valid/invalid data, envelopes, deterministic event application |
| Domain | `SessionService` with an isolated `AppContext` | Admission, missing resources, complete snapshots and post-write events |
| API | Fastify `app.inject()` | Real routing, validation, status and envelope without opening a port |
| Storage | Shared memory/Postgres contract suites | Adapter parity; disposable Postgres also exercises SQL and races |
| Web | Testing Library plus action/proxy tests | Forms, transitions, SSE cancellation and recovery |
| Mobile | Screen hook, store, REST and WS tests | Stale-load ownership, reconnect behavior and shared projection |
| End-to-end | Playwright in `apps/e2e` | Browser flows and deploy smoke; not native device rendering |
| Worker | Runner/handler tests and job contracts | Leases, retries, recurrence, shutdown and idempotence |

Create fresh repositories and event buses per test boundary. Close Fastify, timers, sockets and pools in teardown, even after a failed assertion. Fake timers are useful only when
advanced intentionally and restored; avoid sleeps as synchronization. Mock external effects at an explicit port; prefer the real memory adapter for domain behavior.

Use assertions on outputs and observable effects, not implementation call counts alone. Type assertions in test responses do not replace runtime contract assertions. Preserve tests
for malformed input, unknown errors, stale streams and cancelled jobs.

`pnpm --filter @starter/api test:run` selects API tests; `pnpm test:postgres` runs disposable database coverage; `pnpm test:e2e` runs browser coverage. Inspect scripts and fixture
prerequisites first. Report executed failures separately from unavailable infrastructure.

## Starter example

This excerpt uses the existing implementation; read its source for imports and setup.

Source: `apps/api/src/modules/sessions/__tests__/routes.test.ts`.

```typescript
  it('rejects an invalid body with the canonical error envelope', async () => {
    const response = await app.inject({
      method: 'POST',
      url: '/sessions',
      payload: { name: '' },
    });

    expect(response.statusCode).toBe(400);
    expect(response.json()).toEqual({
      error: { code: 'VALIDATION_FAILED', message: expect.any(String) },
    });
  });
```

## References

- [Vitest patterns](references/vitest-patterns.md)
- [Fixture patterns](references/fixture-patterns.md)
- [React testing](references/react-testing.md)
- [Mock boundaries](references/mock-boundaries.md)

---
name: runtime-inspection
description: Use when debugging TypeScript/Fastify runtime state through HTTP/OpenAPI, /health, logs, SQL, React UI and available local tools.
effort: low
user-invocable: false
---

# Runtime inspection

Use the tools actually connected to the session. The starter does not install an application-inspection MCP server. Missing optional tools are NOT AVAILABLE; never pretend to
evaluate code in a running app.

## Usage

```text
pnpm --filter @starter/api test:run src/modules/sessions/__tests__/routes.test.ts
pnpm --filter @starter/api test:run src/core/__tests__/appIsolation.test.ts
```

## Discovery

Read `package.json`, workspace scripts, `apps/api/src/app.ts`, the registry, environment configuration and running process/log output. Determine the actual host and port without
printing secrets. Confirm the observed process belongs to the intended checkout before attributing behavior to edited code.

## Inspection paths

- HTTP: inspect `/health` and its `data.driver` (memory or postgres), environment and session count. Compare that result with `STORAGE_MODE` and the validated packages/env
  configuration before diagnosing vanished data. Then inspect `/modules`, `/sessions` and the OpenAPI registration in `app.ts`. Use Fastify injection for isolated behavior or a
  known local URL for live behavior. Avoid guessing an endpoint path from another framework.
- Logs: correlate request/session/job IDs and timestamps. Distinguish build artifacts, stale processes, validation failures and actual domain errors. Redact secrets and SQL bindings.
- SQL: inspect schema/migration state and execute bounded read-only queries against a confirmed local database. Prefer disposable test fixtures for writes; do not reset a database.
- UI: inspect the web action→API→SSE path or mobile REST→WS path separately. Browser evidence cannot establish native rendering. Confirm cleanup and stale response ownership.
- Worker: inspect queue state, leases, registry kinds and the active attempt. A timer or process listing alone does not show a successful job.

## Validation loop

Record a hypothesis, one observable probe and its result. Reproduce in the appropriate existing test suite, make the smallest authorized change and rerun the same probe. After
three failed attempts document failed hypotheses and change approach. Keep temporary instances and database writes isolated; clean up only resources created for this investigation.

Output: environment/checkout, commands or tools, expected vs observed behavior, supporting file/line or log evidence, unresolved limits and next test.

## Iron Laws

1. Verify the checkout and process identity before attributing a live response to edited source.
2. Read `/health` and compare its `data.driver` with validated `STORAGE_MODE` before drawing persistence conclusions.
3. Use only connected tools; record missing runtime or native inspection as NOT AVAILABLE.
4. NEVER reset a database or hide a failed probe; isolate test writes and report unavailable checks.

## References

- [Proactive patterns](references/proactive-patterns.md)
- [Tool examples](references/tool-examples.md)
- [Validation checklist](references/validation-checklist.md)

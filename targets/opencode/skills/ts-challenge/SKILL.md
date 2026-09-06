---
name: ts-challenge
description: Use when stress-testing Drizzle changes, React web/mobile interactions,
  worker lifecycle or PR readiness against concrete evidence.
---

# Challenge mode reviews

## Usage

```text
/ts-challenge drizzle
/ts-challenge react
/ts-challenge jobs
/ts-challenge pr
```

## Iron Laws

1. Read changed code and tests before challenging it; cite each failure path.
2. NEVER edit application code during this read-only challenge.
3. Keep prior findings deduplicated and record concrete risk, impact and tradeoffs.

## Adversarial lenses

Check omitted cases, contradiction between implementation/tests/docs, hidden dependency assumptions and the most plausible counterexample to each claim. Do not replace evidence
with rhetorical questioning or arbitrary style preferences.

## Drizzle challenge

Trace the actual write/read transaction and generated migration. Verify constraints, lock scope, previous-schema upgrade, index/query justification, complete DTO projections,
atomic revision metadata and Postgres/memory parity. A service-side count cannot enforce concurrent admission. Never reset a database to make the example work.

## React challenge

Trace user action, pending/error states, event projection and cleanup. Web uses Server Actions/SSE and DOM UI; mobile uses REST/WS/native UI and loading hooks. Check stale requests
after navigation and reconnect ordering. A browser test is not native rendering evidence.

## Jobs challenge

Check sequential batchSize, atomic claim, lease/token fencing, retry/abandon distinction, immutable effect identity, recurrence history and shutdown before pool closure.
At-least-once delivery requires idempotency. The worker cannot import the API or publish through its local bus.

## PR challenge

Review requirements coverage, changed behavior, errors, tests, export/build compatibility and deployment order. The baseline has no authenticated identity; describe required
protection honestly rather than inventing a policy engine.

## Output

Report FINDING id, severity, path/line, trigger, evidence, remedy and regression scenario. End with PASS, PASS WITH WARNINGS or BLOCKED plus unresolved finding count and an
appropriate triage/plan next step. Prior findings must not inflate the new count.

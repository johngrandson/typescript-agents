---
name: ts-quick
description: Use for a contained TypeScript starter fix under roughly 50 lines, such
  as a schema, route or React component edit; expand to planning if boundaries multiply.
---

# Quick mode

## Usage

```text
/ts-quick Clarify the tested SessionService.update JSDoc
pnpm --filter @starter/api check-types
pnpm --filter @starter/api lint
pnpm --filter @starter/api test:run src/modules/sessions/__tests__/service.test.ts
```

## Workflow

1. Read local rules, nearest package.json and the neighboring implementation/test. Confirm the requested behavior and workspace.
2. Make the smallest authorized edit using the existing pattern. A TypeBox field change can affect contracts, API, repositories and both clients; reassess scope before calling it a one-file change.
3. Run the affected package check-types, lint and meaningful existing tests. Use `/ts-verify` to select additional consumer/SQL checks; hooks are not proof that every gate ran.
4. Inspect the diff and report behavior, verification and limits. Commit only working scoped changes when authorized by project/session instructions; never bypass checks.

## Scope escape

Escalate to `/ts-plan` when an invariant, migration, new package boundary or client protocol requires coordination. Preserve the user's existing authorization to continue a bounded
fix; do not invent a planning approval gate for routine choices.

Use Session routes/service/contracts as examples. Expected errors use AppError; web mutations use Server Actions and mobile uses REST. Schema changes use reviewed Drizzle
migrations and disposable Postgres tests, never an automatic database reset.

After three failed attempts stop blind retries, record the failed approaches and investigate the cause. Small changes still need relevant verification; avoid new tests that merely
repeat implementation.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. NEVER bypass tests or reset a database to obtain a passing result.

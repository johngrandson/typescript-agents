---
name: ts-examples
description: Use when asked for TypeScript starter sample code or a walkthrough of
  contracts, Fastify, Drizzle, React web/mobile, jobs, or workflow output.
---

# Examples and walkthroughs

Use the actual Session slice and identify the workspace for every snippet. Pair this skill with the relevant domain skill. Examples illustrate behavior; they are not instructions
to edit the reference checkout.

## Usage

```text
ts-examples Explain SessionService.create and its HTTP contract
ts-examples Compare web Server Actions and mobile ApiService
```

## Select an example

- Contracts: TypeBox schema, Static-derived DTO and shared pure event projection in packages/types.
- API: SessionService with AppContext, thin typed routes, registry and canonical envelopes.
- Persistence: repository port, memory/Postgres parity and generated migration workflow.
- Web: Server Actions through the server-only API client and SSE proxy.
- Mobile: REST/WS services, screen loading ownership and Zustand state. These are not Next Server Actions or DOM components.
- Jobs: registered handlers, sequential JobRunner, fenced leases, recurrence and idempotent archive publication.

Read [verified snippets](references/starter-examples.md) and the adjacent provenance data. Each excerpt cites its exact starter source; describe omitted setup rather than
pretending a partial function is standalone. Validate source hashes against the captured starter snapshot before updating examples.

For a requested capability that does not exist (identity framework, distributed event bus, native device test harness), explain the gap and design implications. Do not fabricate
auth APIs, runtime inspection tools or a third-party queue. Use installed-version official docs only when the local source does not resolve a question.

Workflow demonstrations preserve their own bounds: `ts-plan` writes a plan, `ts-work` implements its tasks, `ts-review` reports findings, and `ts-full` coordinates the complete authorized cycle.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

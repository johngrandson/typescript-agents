# Managed project template

Copy only verified relevant sections inside the managed block. Replace date/version placeholders from current metadata; do not invent installed capabilities.

```markdown
<!-- TYPESCRIPT-STARTER-PLUGIN:START -->
<!-- Updated: {DATE}; harness 1.0.0; stack: {DETECTED_STACK} -->
## TypeScript Starter Harness

Read local rules and workspace manifests before acting. Use /skill:ts-brainstorm for vague requirements, /skill:ts-plan for coordinated changes, /skill:ts-work for an existing plan, /skill:ts-investigate for bugs, /skill:ts-review for read-only findings, and /skill:ts-full for an authorized end-to-end cycle.

Shared TypeBox schemas/Static DTOs live in packages/types. SessionService owns domain decisions; Fastify routes validate/delegate/wrap. AppContext and repository ports are intended architecture. Postgres and memory must satisfy the same contract.

Web uses Server Actions and the SSE BFF proxy. Mobile uses native UI, REST/WS services and loading hooks. Share pure applySessionEvent, not DOM components or server-only modules.

The custom Postgres queue runs sequentially with fenced leases and at-least-once execution. Handlers need idempotency and explicit shutdown. The worker cannot import API modules or use its per-app event bus. clientId is not authenticated identity; no auth or inspection MCP is installed by this harness.

After edits run relevant package check-types/lint/test:run and /skill:ts-verify. SQL, browser, mobile and deployment checks have separate evidence. Never disable tests/hooks or reset a database to hide failure. After three failed attempts document failures and change approach.

Preserve current user authorization. Review/planning artifacts do not authorize publication, push or live deployment.
<!-- TYPESCRIPT-STARTER-PLUGIN:END -->
```

Knowledge routing: domain-resources for vertical operations; fastify-modules for service/route composition; drizzle-patterns for storage; react-patterns for clients;
background-jobs for queue semantics; typescript-idioms for runtime/imports; security/testing/runtime-inspection for their boundaries.

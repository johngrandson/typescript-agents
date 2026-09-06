# Documentation output templates

## Public API

Document purpose; parameters and omitted/null behavior; returned envelope or DTO; expected error codes; effects/ownership; a verified invocation; and the test proving the behavior.
Use JSDoc beside the exported TypeScript declaration. Code in docs must come from the captured starter or a tested implementation.

## README feature section

State user-visible behavior, setup/configuration, supported clients, usage and verification. Link actual entry points. Distinguish available behavior from planned capabilities.

## ADR

Title/date/status, context, decision, alternatives, consequences, rollout/rollback limits and evidence. Cite affected package contracts and tests. For jobs record
at-least-once/idempotency and lease ownership; for realtime record per-app bus scope and web/mobile transport differences.

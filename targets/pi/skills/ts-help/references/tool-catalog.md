# Tool catalog

## Forty public workflows

| Command | Arguments | Trigger |
| --- | --- | --- |
| `/skill:ts-audit` | `[--quick\|--full\|--focus=area\|--since=commit]` | Use when assessing TypeScript starter health across architecture, performance, security, tests and dependencies; supports quick, full, focused and incremental audits. |
| `/skill:ts-boundaries` | `[--assess\|--fix]` | Use when analyzing TypeScript package imports, Fastify module coupling, repository ports, or the impact of splitting a module. |
| `/skill:ts-brainstorm` | `<topic or feature idea>` | Use when a TypeScript starter feature is vague and needs requirements, alternatives or tradeoffs before a plan. |
| `/skill:ts-brief` | `[path to plan file]` | Interactive briefing of a plan file — explains reasoning, schema decisions, component choices. Use when developers need to understand a plan before approving. |
| `/skill:ts-challenge` | `drizzle \| react \| jobs \| pr` | Use when stress-testing Drizzle changes, React web/mobile interactions, worker lifecycle or PR readiness against concrete evidence. |
| `/skill:ts-codex-loop` | `[--base <branch>] [--uncommitted] [--auto] [--max-rounds N]` | Use when the Codex CLI should review TypeScript starter changes in a bounded review, fix and verify loop before a PR. |
| `/skill:ts-compound` | `[description of what was fixed]` | Use after a verified fix to capture a searchable TypeScript starter solution with root cause, evidence and prevention. |
| `/skill:ts-deploy` | `—` | Use when editing Docker/Compose, production builds, environment validation, migrations, health checks, graceful shutdown, or deployment smoke tests. |
| `/skill:ts-deps-audit` | `[--all \| --base REF \| --preview PACKAGE...] [--quick] [--offline] [--strict] [--json] [--sarif PATH] [--ci] [--no-differential] [--no-llm \| --llm]` | Audit pnpm lock changes and npm package bytes for supply-chain risks, lifecycle effects, publisher changes and advisories. Use after dependency changes, on lockfile PRs, or to preview candidates without installation. |
| `/skill:ts-deps-update` | `[--pkg NAME[@VERSION]] [--scope IMPORTER] [--dry-run] [--prepare-only] [--offline]` | Update pnpm dependencies safely by importer with compatible patches, lock preparation, security audit and verification. Use when upgrading packages, reviewing outdated dependencies or preparing a maintenance PR. |
| `/skill:ts-deps-vet` | `--seed \| --list \| --check \| --artifact ID --run REPORT --decision DECISION --criterion CRITERION --reason TEXT` | Record dependency review evidence in dependency-vet.json after a pnpm/npm security audit. Use to inspect, seed, check, clear a justified finding or record an explicitly authorized accepted risk. |
| `/skill:ts-docs-fetcher` | `PACKAGE --importer PATH [--query API] [--url OFFICIAL_URL --url-version VERSION] [--offline]` | Fetch official docs, TypeScript declarations and changelogs for exact npm versions resolved by pnpm. Use for package API research, including Fastify registration, React hooks and Drizzle queries, or upgrade compatibility. |
| `/skill:ts-document` | `[plan-file OR feature-name]` | Use when documenting tested TypeScript APIs, TypeBox contracts, Fastify/OpenAPI behavior, README sections or ADRs; not for docs lookup. |
| `/skill:drizzle-constraint-debug` | `—` | Use when a Postgres SQLSTATE or named unique, foreign-key, check, or not-null constraint fails through Drizzle. |
| `/skill:drizzle-n1-check` | `—` | Use when N+1 queries are suspected in repository calls inside loops or repeated SQL per parent record; not for unrelated database performance. |
| `/skill:ts-examples` | `—` | Use when asked for TypeScript starter sample code or a walkthrough of contracts, Fastify, Drizzle, React web/mobile, jobs, or workflow output. |
| `/skill:ts-freeze` | `—` | Scope or freeze which files Claude can edit during debugging, a refactor, or review. Use when edits should stay in specific dirs, or for a read-only investigate lock. Backed by a sentinel + PreToolUse hook. |
| `/skill:ts-full` | `<feature description> [--codex]` | Use when delivering a new coordinated starter feature through planning, implementation, verification, review and solution capture; existing plans route to work. |
| `/skill:ts-help` | `[description of what you want to do]` | Use when choosing a TypeScript Starter Harness workflow for planning, debugging, review or verification; not for bare /help or a plugin tour. |
| `/skill:ts-init` | `[--update]` | Use when installing/updating TypeScript starter project rules, Fastify/Drizzle/React skill routing, verification guidance or managed review guidelines. |
| `/skill:ts-intro` | `[--section N]` | Use for a six-section tour of TypeScript Starter Harness commands, domain guidance, agent roles and workflow limits. |
| `/skill:ts-investigate` | `<bug description> [--parallel]` | Investigate bugs and errors in TypeScript starter — root-cause analysis for crashes, exceptions, stack traces, test failures. Use --parallel for deep 4-track investigation. |
| `/skill:ts-learn-from-fix` | `[--library <npm-package> --scope personal\|project] <lesson>` | Use after a verified correction to capture a concise TypeScript lesson or npm library rule with explicit project/personal scope. |
| `/skill:ts-narrow-catch` | `[file_path \| directory \| --all]` | Use when auditing broad catch blocks that swallow programmer errors, misclassify unknown failures, or retry permanent storage/job errors. |
| `/skill:ts-perf` | `[path] [--focus drizzle\|react\|runtime\|jobs]` | Use when measuring starter SQL/API latency, event-loop stalls, retained React state, mobile transport delays, or worker throughput. |
| `/skill:ts-permissions` | `[--days=14] [--dry-run]` | Use when reviewing recent shell commands to propose narrowly scoped runtime permissions based on actual pnpm scripts and their effects. |
| `/skill:ts-plan` | `<feature description OR path to review/plan file>` | Use when planning coordinated changes across shared contracts, database, Fastify API, Next web, Expo mobile, realtime or jobs. |
| `/skill:ts-pnpm-compression` | `—` | Use when verbose pnpm, Turbo, TypeScript, ESLint or Vitest output obscures errors; retain raw logs and original command exit status. |
| `/skill:ts-pr-review` | `<PR number or URL> [--fix] [--bots-only] [--no-resolve]` | Use when reviewing GitHub PR feedback, applying authorized TypeScript fixes, verifying tests and preparing replies or thread resolution. |
| `/skill:ts-quick` | `—` | Use for a contained TypeScript starter fix under roughly 50 lines, such as a schema, route or React component edit; expand to planning if boundaries multiply. |
| `/skill:react-state-audit` | `path/to/component-or-hook.tsx` | Use when React or React Native retains stale state, duplicate snapshots, unbounded lists, listeners, sockets, or timers after navigation. |
| `/skill:ts-recall` | `<question about past work>` | Use when recalling prior starter work from solution docs, Git history or an available session-history tool, with cited evidence. |
| `/skill:ts-research` | `—` | Use when investigating TypeScript starter patterns or evaluating npm packages against official sources and resolved versions. |
| `/skill:ts-review` | `[test\|security\|jobs\|deploy\|iron-laws\|all]` | Use after implementation for read-only review of requirements, TypeScript correctness, security, tests and affected starter domains. |
| `/skill:ts-techdebt` | `—` | Use when assessing duplicated contracts, leaky service/repository boundaries, unused dependencies, or avoidable TypeScript starter complexity. |
| `/skill:ts-trace` | `—` | Use when tracing a TypeScript symbol from API routes, web actions/hooks, mobile services/screens or worker handlers, including arguments and effects. |
| `/skill:ts-triage` | `[path to review file]` | Triage review findings interactively — approve, skip, or prioritize each issue. Use after /skill:ts-review to filter findings before fixing. |
| `/skill:ts-verify` | `—` | Use after TypeScript starter edits to verify workspace typechecks, ESLint, Vitest tests, schema contracts and relevant integration gates. |
| `/skill:ts-watch-pr` | `<PR number or URL> [--checks-only] [--fix]` | Use when watching GitHub PR check/review deltas, resuming event cursors or running bounded authorized Codex cloud review rounds. |
| `/skill:ts-work` | `<path to plan file>` | Use when executing a TypeScript starter plan, resuming with --continue or --from, and verifying tasks/phases with package checks and tests. |

## Eleven knowledge skills

| Skill | Trigger |
| --- | --- |
| `background-jobs` | Use when editing the custom Postgres job queue, worker handlers, registry, retries, leases, recurrence, idempotency, or shutdown behavior. |
| `compound-docs` | Use when searching verified TypeScript/Fastify/Drizzle solution docs by symptom, component or root cause before a repeated investigation. |
| `domain-resources` | Use when designing a domain operation across shared TypeBox contracts, Fastify services, Drizzle repositories, effects, and clients. |
| `drizzle-patterns` | Use when editing Drizzle schemas, SQL queries, transactions, migrations, indexes, repository ports, or Postgres/memory contract parity. |
| `fastify-modules` | Use when editing Fastify routes, services, module registration, AppContext composition, error envelopes, or API module boundaries. |
| `intent-detection` | Use when a starter request combines intents or is unclear about planning, debugging, reviewing or implementing across API, web, mobile and jobs. |
| `react-patterns` | Use when editing Next.js React or Expo/React Native UI, forms, state, navigation, subscriptions, SSE/WS recovery, or shared event projection. |
| `runtime-inspection` | Use when debugging TypeScript/Fastify runtime state through HTTP/OpenAPI, /health, logs, SQL, React UI and available local tools. |
| `security` | Use when reviewing input validation, SQL injection, error exposure, storage paths, stream boundaries, secrets, or a proposed authentication/authorization boundary. |
| `testing` | Use when writing or repairing Vitest, Fastify inject, repository contract, Testing Library, Playwright, or asynchronous lifecycle tests. |
| `typescript-idioms` | Use when designing strict TypeScript modules, schemas, async control flow, unknown errors, Node lifecycle, or imports across Fastify/React workspaces. |

Compatibility aliases: `/skill:drizzle-n1-check`, `/skill:drizzle-constraint-debug`, `/skill:react-state-audit`. The main Claude commands are `/skill:drizzle-n1-check`,
`/skill:drizzle-constraint-debug`
and `/skill:react-state-audit`; portable specialized names keep their drizzle/react prefix. Other public portable names use ts-. Read runtime support for actual agent/hook
availability.

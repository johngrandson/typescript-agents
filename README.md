# TypeScript Starter Harness

Local development workflows for applications built with Node, TypeScript,
Fastify, TypeBox, Next.js, React, Expo, React Native, Turborepo, Drizzle and
PostgreSQL.

The harness has 51 skills, 26 specialist agents and 23 hook responsibilities.
Claude Code uses the canonical plugin. Generators produce distributions for
Amp, Codex, Pi, OpenCode and DeepSeek Harness (dsh), preserving each runtime's
supported capabilities. See the [runtime matrix](docs/runtime-support.md).

## What it understands

| Area | Project contract |
| --- | --- |
| Shared contracts | TypeBox schemas and runtime validation in `packages/types`; explicit ESM entry points |
| API | Fastify modules with schemas, services, routes and module registration |
| Database | Drizzle schema/migrations; matching memory/PostgreSQL repository behavior |
| Web | Next.js and React; Server Actions for the API funnel and BFF streaming |
| Mobile | Expo/React Native; REST/WS services, hooks, Zustand and navigation |
| Realtime | In-process API bus, stream lifecycle, cancellation and client recovery |
| Jobs | Sequential PostgreSQL worker; lease fencing, retries, recurrence and idempotency |
| Tooling | pnpm, Turbo, ESLint, Prettier, Vitest, Testing Library, Playwright and Knip |

Guidance follows actual source and lockfile versions. Web and mobile React
versions differ. The starter has no built-in authentication; a socket `clientId`
is not an authenticated identity. Worker execution is at least once, so side
effects need idempotency. See the
[reference snapshot](docs/reference/starter-snapshot.json).

## Local installation

This repository is an independent local distribution. Install it from the
checkout; no hosted repository or package registry release is required.

### Claude Code

Run from this repository:

```bash
claude plugin marketplace add "$PWD"
claude plugin install drizzle@typescript-starter-harness
claude plugin install react@typescript-starter-harness
claude plugin install typescript-starter@typescript-starter-harness
```

Start a new session in your application repository, then use:

```text
/ts:plan Add a session archive workflow
/ts:work .claude/plans/session-archive/plan.md
/ts:verify
/ts:review
/drizzle:n1-check packages/db
/react:state-audit apps/mobile/src
```

The main namespace is `ts`; the `drizzle` and `react` plugins provide three
compatibility commands. `catchup` remains a separate, optional plugin with its
own version and behavior.

### Other runtimes

| Runtime | Local source | Workflow invocation | Installation guide |
| --- | --- | --- | --- |
| Amp | `targets/amp` | Skill `ts-plan`, paired wrapper `ts: plan` | [Amp](docs/amp.md) |
| Codex | `targets/codex` | `$typescript-starter:ts-plan` | [Codex](docs/codex.md) |
| Pi | `targets/pi` | `/skill:ts-plan` | [Pi](docs/pi.md) |
| OpenCode | `targets/opencode/skills` | Load native skill `ts-plan` | [OpenCode](docs/opencode.md) |
| dsh | `targets/dsh/skills` | `/ts-plan` | [dsh](docs/dsh.md) |

Install and update from matching generated trees. Restart the runtime after
changing installed files; an existing session may keep its discovery catalog.

## Workflows

Use `/ts:help` for routing and `/ts:intro` for the lifecycle. Public commands
cover planning, implementation, verification, review, investigation, dependency
auditing, deployment, documentation and learning from fixes.

- Plan/work/full keep durable task state and bounded retry loops.
- Review/investigate preserve read-only boundaries until a fix is authorized.
- `deps-audit`, `deps-vet` and `deps-update` separate analysis, explicit approval
  and lockfile changes. Cached or synthetic evidence does not approve a package.
- `runtime-inspection` uses source, tests, logs and optional local HTTP probes.
- `freeze` constrains Claude edits; other runtimes expose an advisory scope,
  with the separate Amp plugin providing its own limited native lock.

The [inventory](docs/quality/inventory.json) records all 51 skills and 26
agents. Hooks and their limits are described in [HOOKS.md](HOOKS.md).

## Develop the harness

Use Node 22.19 or later, pnpm 10.6.5, Python 3.12 and Bash. Bun runs the Amp
protocol test harness; the application remains Node-based.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
corepack enable
pnpm install --frozen-lockfile
pnpm verify
```

Lefthook installs the pre-commit checks. Do not bypass them. `pnpm verify` runs
local lint, inventory/manifest validation, tests, generator drift checks,
reviewed snapshots and structural evaluations. Every skill and agent must reach
0.95. A structural score does not measure model-trigger accuracy.

Edit canonical skills, agents and hooks under `plugins/typescript-starter`.
Do not hand-edit generated targets. After changing canonical content:

```bash
make amp-skills codex-skills pi-skills opencode-skills dsh-skills
# Review the generated diff, including resource bytes and executable modes.
make generated-skills-snapshots
make generated-skills-sync
pnpm verify
```

`make generated-skills-sync` checks golden snapshots; it does not accept new
snapshots automatically. Generation is atomic and preserves the previous tree
when validation fails.

Optional `make <runtime>-runtime-smoke` commands use isolated runtime state.
Model-trigger evaluations use `make eval-triggers` and require a fresh run with
at least 75% accuracy for **each** skill. They can incur provider costs and are
separate from the local gate. Registry cassette refresh is also separate and
runs only when `ENABLE_REGISTRY_CASSETTE_REFRESH=true` is set in the repository.

[Verification](docs/quality/verification.md) records observed checks and their
limits. [Example verification](docs/reference/example-verification.md) records
the captured source examples. Registry capture uses
`config/registry-capture-packages.json` and optional responses under
`tests/fixtures/registry-cassettes`.

Maintained by João. Licensed under the [MIT License](LICENSE).

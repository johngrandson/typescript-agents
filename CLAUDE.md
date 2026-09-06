# TypeScript Starter Harness — contributor instructions

This repository is a development harness, not the application starter.
`plugins/typescript-starter` is canonical; `targets/{amp,codex,pi,opencode,dsh}`
are generated projections. Use `docs/reference/starter-snapshot.json` for the
captured reference application and `docs/reference/example-verification.md` for
the source examples. Do not depend on a maintainer's personal checkout path.

## Project boundaries

- Preserve 51 skills, 26 agent responsibilities and 23 hook responsibilities.
- Claude uses `/ts:*`, with `/drizzle:n1-check`, `/drizzle:constraint-debug` and
  `/react:state-audit` aliases. Generated public workflows use `ts-*`, with
  those three specialist names unprefixed. Eleven knowledge skills stay private.
- Keep `catchup` independent, with its own version. João maintains all plugins.
- Keep generic Python, Bash, Make and pytest infrastructure. Harness package
  management is pnpm; Lefthook owns the existing pre-commit checks.
- Publish only when explicitly requested. Local development does not authorize
  a push or release.

## Source facts

1. Read workspace manifests, the lockfile, Turbo tasks and source before
   naming APIs or proposing commands. Older application docs can be stale.
2. Shared contracts use TypeBox and ESM exports. Fastify modules separate
   schemas, service logic, routes and registry setup.
3. Drizzle/PostgreSQL and memory repositories must satisfy the same behavior.
   Schema changes need migrations and disposable database verification.
4. Web requests use the Next.js Server Action/BFF boundary. Mobile uses its own
   REST/WS services, hooks, Zustand and React Navigation. Do not apply web
   effect-loading restrictions to mobile.
5. The API realtime bus is local to an application instance. Handle stream
   teardown, backpressure, cancellation and recovery explicitly.
6. PostgreSQL jobs are at least once. Preserve lease fencing, idempotency,
   recurrence, retry and shutdown behavior. No global execution guarantee or
   built-in authentication should be invented.
7. Application verification is `pnpm verify`; build, PostgreSQL, browser/mobile
   and deployment checks remain separate where the package scripts say so.

## Skills and agents

A skill lives at `skills/<name>/SKILL.md` with valid YAML frontmatter. Keep its
`name` equal to its directory, its description below 250 characters, and its
public/private discovery flag intact. Describe both what it does and when to
use it. Keep task controls, inputs, state transitions, output contracts and
failure behavior when moving details into references.

Reference packaged files with `${CLAUDE_SKILL_DIR}/references/...`. Use real
TypeScript examples and commands supported by the target workspace. Include
concrete rules and examples; never add filler solely to satisfy a score.

Agents keep explicit tools, model, effort, permission mode and preloaded skills.
Qualify concrete Claude subagent calls as `ts:<agent-name>`. Read-only
specialists can report findings through their existing designated output
contract; they must not modify application code. Orchestrators keep depth
checks, sequential fallbacks, bounded retry counters and durable progress.

## Runtime support

Each runtime has a separate capability contract in `docs/runtime-support.md`.
Do not assume that loading skill text installs custom agents, hooks, a task API,
MCP servers or root instructions. Portable workflows must complete through
sequential local work when optional native subagents are absent.

Amp has five enforced read-only specialists and a bounded verification gate
activated only by its paired `ts: full` wrapper. Codex carries one optional
synchronous safeguard. Pi/OpenCode/dsh do not inherit the Claude hook graph.
Keep watcher state, duplicate-event handling, cancellation and credential-file
permissions intact when updating the Amp plugins.

## Verification and commits

1. Make a focused change and run the relevant existing tests.
2. Run `pnpm lint`, offline validation and structural skill/agent evaluations.
   Every skill and agent must score at least 0.95; do not lower checks to hide
   missing behavior. Fresh model-trigger accuracy is a separate per-skill gate.
3. Regenerate all affected targets. Review bytes, paths and executable modes,
   then update golden snapshots deliberately and check them again.
4. Run `pnpm verify` before completing an integration. Keep optional runtime,
   provider, database and mobile checks distinct from executed local checks.
5. Commit working increments with their matching generated files. Never use
   `--no-verify`, disable a failing test, commit non-compiling code or reset a
   database without user authorization.

After three failed attempts, stop that approach, record failures and investigate
an alternative. Do not retry blindly. Keep `docs/quality/inventory.json`,
`docs/quality/coverage.json`, `docs/quality/verification.md`,
`docs/reference/starter-snapshot.json` and
`docs/reference/example-verification.md` current. Harness helpers live under
`scripts/harness_lib`; offline validation runs through
`scripts/validate_harness.py`. Keep the main regression groups in
`scripts/tests/test_typescript_harness.py` and
`scripts/tests/test_dependency_workflows.py`.

## Useful commands

```bash
pnpm verify
make test-quick
make eval-skills eval-agents
make validate
python3 -m pytest scripts/tests/test_typescript_harness.py \
  scripts/tests/test_dependency_workflows.py
make amp-skills codex-skills pi-skills opencode-skills dsh-skills
make generated-skills-snapshots
make generated-skills-sync
```

`make eval-triggers` invokes a model and may cost money; it is not part of the
hermetic local gate. Registry capture requires explicit opt-in and never vets
packages. Review dependency ledger writes separately from audit execution.

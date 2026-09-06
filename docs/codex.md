# Codex installation

The native plugin is generated at `targets/codex`. It contains 51 skills,
packaged references/scripts and one optional synchronous destructive-command
safeguard. See the [capability matrix](runtime-support.md).

## Install from this checkout

```bash
codex plugin marketplace add /absolute/path/to/typescript_starter_harness
codex plugin add typescript-starter@typescript-starter-harness
```

Start a new Codex session in the application repository. Use the skill selector
or a fully qualified reference:

```text
$typescript-starter:ts-plan Add an archive operation
$typescript-starter:ts-work .claude/plans/archive/plan.md
$typescript-starter:ts-review
$typescript-starter:drizzle-n1-check packages/db
```

The manifest namespace is `typescript-starter`; Claude's `ts` namespace is
independent. Plugin-owned skill mentions are qualified in generated text.

## Behavior and updates

Custom agents and the full Claude hook graph are not installed. Plan, work,
investigate, review and full lifecycle workflows use durable files and can run
sequentially. Native generic subagents are optional.

The optional hook keeps synchronous JSON decisions and packages its Python
helper. Host trust/approval settings determine whether it runs. A generated
freeze skill establishes an advisory conversation scope, not the Claude
sentinel. No MCP service is installed or required.

After regenerating this checkout, refresh or reinstall the local marketplace
plugin using the installed CLI's plugin commands, then start a fresh process.
Do not assume that an existing session refreshes its catalog. Remove only this
plugin when uninstalling; preserve unrelated plugins and personal state.

## Verify

```bash
make codex-skills-validate
make codex-runtime-smoke
```

The optional smoke runner installs, lists and removes the plugin inside isolated
Codex state. Its manifest validation and resource tests are distinct from a live
model run. Current results are recorded in
[the verification record](quality/verification.md).

# Runtime support

The canonical TypeScript starter plugin has 51 skills and 40 public workflows.
Five generated targets preserve the same domain responsibilities. Runtime
capabilities differ; installing skills alone does not install agents or hooks.

| Capability | Claude Code | Amp | Codex | Pi | OpenCode | dsh |
| --- | --- | --- | --- | --- | --- | --- |
| Skills and packaged resources | 51 | 51 | 51 | 51 | 51 | 51 |
| Public workflow entry points | 40 | 40 local wrappers | Native skills | Native skills | Native skills | Native slash injection |
| Custom specialists | 26 | Five read-only | Not installed | Not installed | Not installed | No Markdown agent registry |
| Hooks/enforcement | 23 responsibilities | Edit lock and paired-full gate | One optional safeguard | Not installed | Not installed | Not installed |
| Sequential workflow fallback | Yes | Yes | Yes | Yes | Yes | Yes |
| Generated drift/mode checks | Canonical | Yes | Yes | Yes | Yes | Yes |
| Golden snapshots | Canonical | Yes | Yes | Yes | Yes | Yes |
| Root instructions | Plugin contract | Not installed | Not installed | Not installed | Not installed | Native `CLAUDE.md` discovery |

## Invocation

| Runtime | Main workflow | Specialist example |
| --- | --- | --- |
| Claude | `/ts:plan` | `/drizzle:n1-check` |
| Amp | Native skill `ts-plan`; local `ts: plan` wrapper | `drizzle: n1-check` wrapper |
| Codex | `$typescript-starter:ts-plan` | `$typescript-starter:drizzle-n1-check` |
| Pi | `/skill:ts-plan` | `/skill:drizzle-n1-check` |
| OpenCode | Load native skill `ts-plan` | Load `drizzle-n1-check` |
| dsh | `/ts-plan` | `/drizzle-n1-check` |

The primary Claude commands `/ts:drizzle-n1-check`,
`/ts:drizzle-constraint-debug` and `/ts:react-state-audit` resolve to the same
portable names as their aliases. Knowledge skills retain their canonical names.

## Runtime boundaries

Claude keeps the full hook event graph, specialized agents, task orchestration
and project sentinel behavior. The hooks inspect the actual workspace/package,
use bounded probes and never make edits merely to format a file.

Amp's **paired-full** profile installs matching local skills and plugins. It
preserves all 40 wrappers and the verification follow-up activated by the
`ts: full` wrapper. The **hosted-native** profile can discover hosted skills,
but local wrappers cannot resolve hosted-only files and native `ts-full` skill
invocation does not arm that gate. Five child specialists have `Read`/`finder`
only; independent review/investigation tracks are bounded. The native edit lock
covers Amp-classified edits and disables shell while active; it is not complete
Claude hook parity. A separate PR watcher plugin has durable state, a bounded
keep-alive lease and same-thread delivery. Hosting/publication is a separate,
explicit operation; this checkout does not claim a hosted distribution.

Codex packages skills and one optional synchronous safeguard. Its helper is
packaged with the shell entry point. Installation does not activate the other
Claude hooks, agent definitions, root instructions or any MCP server. Native
subagents remain optional; the sequential lifecycle is complete.

Pi installs skills only. No extensions, prompt templates, custom-agent registry
or bundled MCP configuration are part of the generated package.

OpenCode installs skills only. Discovery and restart behavior depend on the
installed host. The generator validates names, descriptions and references;
it does not register separate commands, hooks, agents or MCP servers.

dsh discovers one level of `<name>/SKILL.md` bundles in its scanned roots.
Copy the contents of `targets/dsh/skills`, not a nested checkout. A bounded
`/name` token naming a public skill can be injected by the host before a model
step. dsh reads `CLAUDE.md` natively, but no hook bridge or custom-agent registry
is installed by this target. Advanced `customSkillDirs` configuration must also
account for which skill-filesystem provider the active profile enables.

## Local installation and verification

Use the [Amp](amp.md), [Codex](codex.md), [Pi](pi.md), [OpenCode](opencode.md) or
[dsh](dsh.md) guide. All installation paths refer to this local checkout.
Start a fresh process after install, update, ref changes, clean reinstall or
uninstall. A separate list/debug command does not refresh an existing session.

`make <runtime>-runtime-smoke` isolates host state and checks discovery,
packaged bytes, executable modes and lifecycle behavior. Protocol tests use
fixtures and fake clocks; they do not prove a live provider interaction.

The [verification record](quality/verification.md) lists the exact commands
that were run and their limits. Fresh model-trigger evaluation, mobile or
device checks and external services remain separate when they are not run.

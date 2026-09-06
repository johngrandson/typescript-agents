# Hooks

The TypeScript starter plugin has 23 hook responsibilities across ten lifecycle
events. Claude Code runs the complete set. The optional Codex safeguard carries
the destructive-command gate; other runtimes retain their documented native
capabilities and workflow guidance.

The canonical implementation is
[`plugins/typescript-starter/hooks/`](plugins/typescript-starter/hooks/).
Each executable Bash entrypoint delegates to a bundled Python standard-library
runtime. Event JSON is parsed as data. Hooks never install packages, run builds,
start servers or containers, migrate databases, or call a model. The only network
operations are a bounded Git fetch and one local API health request. The only
quality subprocess after an edit is local Prettier in check mode.

## Scope and outputs

Application hooks recognize an ancestor containing `pnpm-workspace.yaml`,
`package.json`, `turbo.json`, and a TypeScript dependency in the manifests. They
use declared workspace members and the affected file's package, regardless of
the project name. Relative file paths use the event's `cwd`; workflow state uses
the workspace root. Existing and new paths are canonicalized to prevent symlink
or `..` escapes. Generated files, dependency trees and project ignores are
excluded. Code hooks accept TS/TSX/MTS/CTS and JS/JSX/MJS/CJS.

Outside that workspace, application hooks are silent. Force-push protection
remains global, an explicitly configured freeze still applies, and existing
`.claude/plans` retain their recovery hints.

Intentional denials use JSON `permissionDecision: "deny"` and exit zero.
Post-edit warnings use stderr and exit two. `UserPromptSubmit` always exits zero;
`Stop` uses `systemMessage` so the turn can end normally. `StopFailure` records a
short note in a scratchpad because that event does not consume output. A missing
tool or incidental inspection error is never recorded as a successful check.
The dependency gate separately enforces an explicitly configured policy when
its required evidence is unavailable.

## Event inventory

| Event | Responsibilities |
| --- | --- |
| `PreToolUse` | `block-dangerous-ops`, `deps-audit-gate`, `freeze-gate` |
| `PostToolUse` | `check-format`, `iron-law-verifier`, `debug-statement-warning`, `security-reminder`, `plan-stop-reminder`, `log-progress` |
| `PostToolUseFailure` | `typescript-failure-hints`, `error-critic` |
| `SessionStart` | `setup-dirs`, `detect-domain-resources`, `detect-runtime-tools`, `check-scratchpad`, `check-resume`, `check-branch-freshness` |
| `UserPromptSubmit` | `route-intent` |
| `SubagentStart` | `inject-iron-laws` |
| `PreCompact` | `precompact-rules` |
| `PostCompact` | `postcompact-verify` |
| `StopFailure` | `stop-failure-log` |
| `Stop` | `check-pending-plans` |

Registrations combine extension groups inside each script, avoiding duplicate
checks for the same event and file. All ten events and 23 responsibilities are
retained; the manifest has 26 command registrations.

## Safety and code checks

The global gate recognizes literal `git push --force` and `-f`, allowing
`--force-with-lease`. Within the workspace it also recognizes forced Drizzle
pushes, `dropdb`, explicit destructive SQL passed to database clients, and
project Compose volume removal. It reads direct pnpm/Turbo script wrappers as
data. Quoted mentions in `echo` are not executable commands. Cyclic scripts,
dynamic shell and arbitrary wrappers are outside its limited classifier; a
command receiving no denial is not a security certification. Production builds
and ordinary migration/generation commands are not classified as resets.

Freeze reads `.claude/.freeze`. An empty file blocks editing tools; directory
lines allow only those canonical directory trees. `/ts:freeze` manages that
explicit scope. Bash mutations are outside this freeze gate's coverage.

The dependency gate delegates cache validation to the audit driver and uses
`dependency-vet.json` plus `.claude/deps-audit`. Missing policy is advisory.
Configured mandatory policy requires valid evidence for the exact resolved
state. Lock preparation requires `--lockfile-only --ignore-scripts
--ignore-pnpmfile`; a previous audit cannot approve a newly resolving update.
See [dependency auditing](plugins/typescript-starter/skills/deps-audit/SKILL.md).

Code warnings inspect introduced syntax for central env access, web client
imports, direct web component fetches, raw HTML/SQL, explicit monetary floating
columns and module-level timers. Comments and literal text are excluded.
The Expo public URL adapter and type-only imports retain their exceptions.
Debug calls invite review because `no-console` is off. The shared ESLint
configuration remains the authority for lint/type rules. No textual hook
claims to prove authorization, stale-response protection or job fencing.

Prettier resolves the file's own config and project ignores. Valid or ignored
files are silent. Invalid formatting, missing tooling, internal failures and
timeouts receive distinct messages. The hook never writes a file.

## Recovery and limits

Plans retain `plan.md`, `progress.md` and `scratchpad.md`. Planning-only work ends
by presenting its result; execution already authorized can continue. Creating a
plan or compacting context does not impose a new approval checkpoint. Full mode
is recognized by the existing `**State**:` field in `progress.md`.

Scratchpad reporting and API-failure recovery use modification order; compaction
selects the first pending plan. These heuristics do not authorize work on another
plan. Scratchpad counts refer to all bullet entries, not only dead ends. Edit
metrics use real JSON serialization under `${CLAUDE_PLUGIN_DATA}/skill-metrics/`
and never append to plan progress.

Repeated failures are keyed by root, session, command and package/filter. The
first is silent, the second warns, and the third requires documenting failures,
researching alternatives and changing approach. Five sanitized entries are
retained; full errors, credentials, env values and SQL parameters are not saved.

## Contributor references

- [Entry points and event transport](plugins/typescript-starter/hooks/README.md)
- [Safety gates](plugins/typescript-starter/hooks/docs/safety-gates.md)
- [Code quality](plugins/typescript-starter/hooks/docs/code-quality.md)
- [Failure recovery](plugins/typescript-starter/hooks/docs/failure-recovery.md)
- [Context injection](plugins/typescript-starter/hooks/docs/context-injection.md)
- [Session lifecycle](plugins/typescript-starter/hooks/docs/session-lifecycle.md)
- [Workflow state](plugins/typescript-starter/hooks/docs/workflow-state.md)

# Hook contributor guide

The 23 Bash entrypoints in `scripts/` delegate to `hook_runtime.py`. Python 3
standard-library modules perform parsing, confined path resolution, JSON output
and bounded subprocess execution. There is no application import or evaluation.
The dependency gate calls the audit driver's offline `--gate-check` contract.

Use [the user guide](../../../HOOKS.md) for behavior and scope, and
[the event configuration](hooks.json) for matchers, timeouts and dispatch.
These links are relative to this directory under `plugins/typescript-starter`.

## Event transport

| Event | Output |
| --- | --- |
| `PreToolUse` | JSON permission decision and additional context; exit 0 |
| `PostToolUse` | stderr with exit 2 for an actionable warning |
| `PostToolUseFailure` | JSON `hookSpecificOutput.additionalContext`; exit 0 |
| `UserPromptSubmit` | JSON additional context; always exit 0 |
| `SubagentStart` | JSON additional context; exit 0 |
| `SessionStart` | stdout context; exit 0 |
| `PreCompact` | JSON `systemMessage`; exit 0 |
| `PostCompact` | stderr with exit 2 when pending context needs rereading |
| `StopFailure` | scratchpad write only; exit 0 |
| `Stop` | JSON `systemMessage`; exit 0, normal stop continues |

`hooks.json` retains each event's timeout and asynchronous settings. Each Edit
and Write responsibility runs once, with the union of code extensions checked
inside the script. There are 26 command registrations, reduced from 30 by
removing duplicated formatting and rule-check registrations. The always-on
command gate retains `|| exit 0`; intended denials must never use a failing
process status. Mandatory dependency policy uses its own unavailable-evidence
handling and cannot be satisfied by a parser error or empty cache.

## Parsing and limitations

Workspace discovery reads shallow patterns declared in the pnpm packages list,
including exclusions. Recursive `**` membership is not traversed in hooks.
Direct shell commands and literal package scripts are classified without
executing them. Unknown wrappers, shell expansions and cyclic script graphs do
not prove safety. The code scanner excludes comments, string/template text and
regex bodies. It provides a bounded syntactic review, not an AST/type/data-flow
proof; template interpolations and ambiguous edit locations require contextual
review. Existing-source context is read only to establish client directives and
timer scope; rule findings still concern introduced content.

The canonical files and generated safeguard must include `hook_runtime.py` next
to their wrappers. Codex copies only the destructive-command entrypoint and that
helper. Other runtimes do not inherit Claude lifecycle enforcement automatically.

## Verification

Run the fixture suite without starting application services or installing tools:

```bash
.venv/bin/python -m pytest plugins/typescript-starter/hooks/tests/test_hooks.py
bash plugins/typescript-starter/hooks/tests/block-dangerous-ops_test.sh
```

Fixtures replace external commands and inspect argv. They test quote handling,
workspace/package selection, confinement, event transport, nonwriting format
checks, local health envelopes, recovery state and dependency policy delegation.
Run Bash syntax and ShellCheck on every wrapper after changes. No test executes
force pushes, resets, migrations, deployments or dependency installs.

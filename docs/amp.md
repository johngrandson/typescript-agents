# Amp installation and workflow plugin

`targets/amp` contains 51 skills, the native `typescript-starter.ts` workflow
plugin and `ts-watch-pr.ts`. Both plugins are generated from this checkout.

## Paired local installation

Copy complete skill directories into a supported local skill root, and the
two plugin files into the local Amp plugin root. For a personal installation:

```bash
mkdir -p "$HOME/.agents/skills" "$HOME/.config/amp/plugins"
cp -a /path/to/typescript_starter_harness/targets/amp/skills/. "$HOME/.agents/skills/"
cp -a /path/to/typescript_starter_harness/targets/amp/plugins/*.ts "$HOME/.config/amp/plugins/"
```

Check for collisions first; copy only this harness's directories and preserve
executable resource modes. Keep skills and plugins from the same revision.
The wrapper resolves supported local roots under the current workspace and
personal configuration. Use `amp skills list --json` and `amp plugins list`
to inspect discovery in a fresh process.

Native `skill: invoke` loads `ts-plan`, `ts-review` and other skills. The paired
plugin also provides 40 palette wrappers, including `ts: plan`, `ts: full`,
`drizzle: n1-check` and `react: state-audit`. A wrapper finds the local skill,
records a pending workflow and injects it once on `agent.start`.

## Capability boundaries

The paired `ts: full` wrapper arms a bounded verification follow-up. A native
`ts-full` invocation loads instructions but does not arm the plugin gate.
Verification recognizes successful project pnpm checks and relevant Make
checks; it does not treat arbitrary shell output as proof. Pending verification
processes, edits and continuation limits are tracked explicitly.

Five specialists cover TypeScript, Drizzle, React, security and testing. Child
tools are restricted to `Read`/`finder`, return findings to the parent, and
cannot write reports or execute shell. Parallel review and investigation have
bounded inputs, timeouts and output sizes; missing tracks run sequentially.
Set `TYPESCRIPT_STARTER_AMP_SPECIALIST_MODEL` only to a model supported by the
installed runtime. The plugin validates the override format.

The edit-lock palette command constrains Amp-classified file edits and blocks
shell while active. It validates canonical paths and symlink escapes. Unknown
third-party mutation tools remain outside that classification boundary. The
advisory freeze skill is separate from this native lock and never writes the
Claude sentinel.

The watcher plugin keeps a bounded Orb lease and durable polling state, handles
review/CI events, and delivers updates to the originating thread. Its credential
file has restricted permissions. Preserve cancellation, deduplication, restart
and expiry behavior when updating it; do not publish credentials in reports.

## Hosted profile

Amp can discover personal or workspace hosted skills through native invocation.
Hosted publication is an explicit separate operation. This local distribution
does not claim a published repository or hosted package. Local wrappers cannot
resolve hosted-only skills. Specialists, parallel commands and edit lock do not
depend
on local skill resolution, while the paired-full gate does.

`amp skill add --global` is machine-local, not account-wide hosting. Managed
imports and copied local files have different update provenance. Do not claim
that a copied local skill is managed by a hosted updater.

## Updates and verification

Regenerate, review and replace the matching local skills/plugins, then start a
fresh process. Installation, update, clean reinstall, ref change and uninstall
affect new processes; listing skills does not refresh an existing session.
Remove only this harness's files when uninstalling.

```bash
make amp-target-validate
make amp-runtime-smoke
```

Protocol tests exercise locks, wrappers, child-agent restrictions, verification,
PR polling, event deduplication and keep-alive behavior with isolated fixtures.
The optional native smoke runner uses isolated settings and discovery. Neither
is a paid model-trigger evaluation. See the [runtime matrix](runtime-support.md)
and [verification record](quality/verification.md) for observed results.

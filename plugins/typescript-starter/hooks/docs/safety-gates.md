# Safety gates

`block-dangerous-ops.sh` classifies literal shell commands and direct pnpm/Turbo
scripts without running them. Global force push (`--force` or `-f`) is denied;
`--force-with-lease` and quoted mentions remain allowed. Workspace-specific
checks cover forced Drizzle push, `dropdb`, explicit DROP DATABASE/SCHEMA or
TRUNCATE passed to a database client, and project Compose volume deletion.
Environment assignments, tabs, command separators and subshell delimiters do
not hide a recognized command. Production builds are allowed.

Denials are JSON with reason and recovery context, with exit 0. The manifest's
`|| exit 0` preserves fail-open behavior for incidental command-gate failures.
This limited classifier does not analyze arbitrary programs, dynamic shell or
unknown wrappers. Lack of a denial does not establish target authorization.

`freeze-gate.sh` reads the root `.claude/.freeze` on editing tools only. Missing
means dormant; empty means all edits are frozen. Nonempty non-comment lines
allow directory prefixes, canonicalized with boundary checks. New files,
symlinks and `..` cannot escape the configured tree. Bash is outside this gate.
`/ts:freeze off` or `/ts:freeze <dir>` follows the user's authorized scope.

`deps-audit-gate.sh` reads `dependency-vet.json` and delegates to
`skills/deps-audit/scripts/deps_audit.py --root ROOT --gate-check`. It never
runs network analysis, installs packages or writes successful audit records.
Absent policy is advisory. Mandatory policy denies when the current lock,
ledger, configuration, source coverage or cache cannot be verified. Quick and
fixture audits cannot pass. A resolving update prepares its lock with
`--lockfile-only --ignore-scripts --ignore-pnpmfile`; after auditing that state,
installation uses `--frozen-lockfile`. See the dependency workflow for cache,
vetting and override semantics.

# Harness verification

## Local checks

Run `pnpm verify` after installing the dependencies in the repository README.
This gate runs Markdown lint, Python tests, shell safeguard regressions, offline
inventory/manifest/resource validation, generated target drift checks, reviewed
snapshots and structural evaluations of all 51 skills and 26 agents.
Each skill and agent must score at least 0.95.

`inventory.json` declares skill, agent and hook identities. `coverage.json`
describes active resources and the checks that cover them. Its `active` status
describes inventory, not a successful execution. The validator rejects missing
resources, duplicate ownership, escaping paths and mismatched source snapshots.

```sh
pnpm verify
python3 -m scripts.validate_harness
```

After changing canonical resources, regenerate and review the target diff before
accepting snapshots:

```sh
make amp-skills codex-skills pi-skills opencode-skills dsh-skills
make generated-skills-snapshots
make generated-skills-sync
pnpm verify
```

## Separate checks

Native runtime smoke tests, model-trigger evaluations, registry refresh,
dependency advisory services and application database/browser/mobile checks are
separate operations. A missing or unexecuted check is not a passing result.
Structural evaluations do not measure model-trigger accuracy.

The [reference example observations](../reference/example-verification.md) pin
source excerpts to the captured application. They do not replace current
harness verification.

## Observed local verification

Verified on 2026-09-06 10:30 UTC after updating `LICENSE` and rebuilding
the local history with João as author.

The new root commit `52c9fb9` passed the full `make ci` gate through the
installed Lefthook pre-commit hook:

- Python suite: 561 passed, with no failures or skips.
- Shell safeguard suite: 84 passed, zero failures.
- Inventory, coverage, resource links and native Claude manifests: passed.
- All five generated targets and their reviewed snapshots: passed.
- Structural evaluations: all 51 skills passed the 0.95 threshold; all 26 agents
  scored 1.000. Skill average was 0.984.
- Staged Markdown, JSON and shell checks: passed.

A fresh local clone of `16edd69` matched the committed tree and had a clean
working directory. A scan of every commit found no reference to the previous
maintainer. This clone check covered Git history and file contents; the full CI
gate ran in the workspace using its installed dependencies.

All four plugins identify João in their manifests and marketplace entries.
`LICENSE` identifies João in its copyright notice. The independent `catchup`
version remains `0.1.0`.

The local history starts with a new root commit. The configured GitHub `origin`
URL and Git identity were preserved. Prior commits were archived outside the
repository before the history was rebuilt.

These are local results. Hosted GitHub Actions, native runtime smoke tests,
provider evaluations, registry refresh and application database/browser/device
checks were not run as part of this preparation. The optional SkillSpector scan
was not run because the scanner was unavailable. No push or release publication
was performed.

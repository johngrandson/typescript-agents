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

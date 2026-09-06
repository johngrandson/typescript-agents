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

Verified on 2026-09-06 10:01 UTC in a fresh local clone of `16431f1`.
Dependencies were installed from `requirements.txt` and the frozen pnpm lockfile
in new local environments. No ignored project files were needed.

- `pnpm verify`: passed.
- Python suite: 561 passed, with no failures or skips.
- Shell safeguard suite: 84 passed, zero failures.
- Inventory, coverage, resource links and native Claude manifests: passed.
- All five generated targets and their reviewed snapshots: passed.
- Structural evaluations: all 51 skills passed the 0.95 threshold; all 26 agents
  scored 1.000. Skill average was 0.984.
- Markdown lint and local documentation links: passed.

Tool versions were Node v22.23.1, pnpm 10.6.5,
Python 3.12.2, and Bun 1.3.14. The initial commit also passed
the full `make ci` release gate through the installed pre-commit hook.
The repository checks also passed Ruff, YAML lint and ShellCheck.

These are local results. Hosted GitHub Actions, native runtime smoke tests,
provider evaluations, registry refresh and application database/browser/device
checks were not run as part of this preparation. The optional SkillSpector scan
was not run because the scanner was unavailable. No push or release publication
was performed.

---
name: deps-update
description: Update pnpm dependencies safely by importer with compatible patches, lock preparation, security audit and verification. Use when upgrading packages, reviewing outdated dependencies or preparing a maintenance PR.
effort: high
argument-hint: "[--pkg NAME[@VERSION]] [--scope IMPORTER] [--dry-run] [--prepare-only] [--offline]"
---

# Dependency updates

Use `/ts:deps-update` to carry out the already authorized dependency maintenance scope. Choose exact importers and packages from the request; no interview is needed for ordinary patches.

## Usage

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/deps_update.py" --root "$PWD" --dry-run
python3 "${CLAUDE_SKILL_DIR}/scripts/deps_update.py" --root "$PWD" --scope apps/api --pkg fastify
python3 "${CLAUDE_SKILL_DIR}/scripts/deps_update.py" --root "$PWD" --scope apps/web --pkg next --prepare-only
```

## Workflow

1. Run `--dry-run` for validated JSON inventory from `pnpm outdated --format json`, collected for root and each importer. Preserve locked/specifier/wanted/latest/peers.
   Treat exit 1 with valid outdated data as expected; fail on malformed output or registry errors.
2. Choose the greatest stable compatible patch by default. Use exact `--pkg NAME@VERSION` only for the deliberately authorized requirement edit; keep unrelated manifests intact.
3. Read exact old/new changelogs, source and peer contracts through `/ts:docs-fetcher` or verified tarballs. Record source URLs, versions, hashes and compatibility notes with
   candidate metadata. Check each consumer's peer requirements and group changes using the [consumer groups](references/update-workflow.md).
4. Preserve distinct Next/React web and Expo/React Native mobile requirements. Select every affected consumer before a shared catalog edit; preserve catalog protocols, package
   aliases and other manifest keys. An incomplete consumer group remains an explicit incompatibility.
5. Save current manifests and lock in run evidence, then prepare `pnpm install --lockfile-only --ignore-scripts --ignore-pnpmfile`. The driver writes only selected requirements
   and catalog entries. If `.pnpmfile.cjs` requires adaptation, stop with that reviewable incompatibility. `--prepare-only` ends after the reviewable lock is generated.
6. Audit the prepared graph before installation. If vetting is missing, leave the prepared state and evidence for `/ts:deps-vet`; continue review and compatibility fixes within
   the authorized scope. A pre-update approval certifies only the old graph.
7. Run `pnpm install --frozen-lockfile`, `pnpm verify` and affected workspace build/test scripts only after the prepared graph satisfies policy. Review declared lifecycle effects
   before enabling execution. Record failures and saved before-state; repair the precise incompatibility without overwriting user edits.
8. Stop after three failed attempts of the same approach, document failures and investigate alternatives. Once verification passes, commit manifests, lock, compatibility changes
   and any authorized policy change together. Prepare PR text with before/after behavior, changelogs, validation and unresolved risks; publication follows session authorization.

## Iron Laws

1. NEVER use global `--latest`, automatic `approve-builds`, disabled peer checks, forced overrides or `dlx` to obtain a passing update.
2. Preserve `pnpm.onlyBuiltDependencies` unless its policy change is explicitly authorized and reviewed; the audit cannot grant that authorization.
3. Keep lock preparation, byte audit, review decisions and lifecycle execution separate. A stale audit or a fixture run cannot approve installation.
4. Preserve user edits and failed prepared evidence. NEVER reset the workspace or commit a failed build to complete this workflow.

## Evidence and resumption

Read `.claude/deps-audit/runs/update-<runId>/` for saved inputs, candidate/group metadata and command outcomes. Resume from the last observed valid state, rechecking the current
manifests and lock before reusing an audit. The executable collects old/new changelog evidence from verified tarballs, checks peers and invokes the audit; missing approval remains
visible for review. See [consumer groups and verification](references/update-workflow.md) for coordinated changes and commit boundaries.

---
name: ts-deps-vet
description: Record dependency review evidence in dependency-vet.json after a pnpm/npm
  security audit. Use to inspect, seed, check, clear a justified finding or record
  an explicitly authorized accepted risk.
---

# Dependency review ledger

Use `/skill:ts-deps-vet` after `/skill:ts-deps-audit` to record actual review conclusions. The ledger lives at
the application root as strict JSON. Never evaluate a ledger as JavaScript, TypeScript or shell, and
never impersonate a human reviewer.

```bash
python3 "scripts/deps_vet.py" --root "$PWD" --seed
python3 "scripts/deps_vet.py" --root "$PWD" --check
python3 "scripts/deps_vet.py" --root "$PWD" --list
python3 "scripts/deps_vet.py" --root "$PWD" \
  --artifact ARTIFACT_ID --run .claude/deps-audit/runs/RUN_ID/report.json \
  --decision cleared --criterion safe_to_deploy --reason 'Concrete reviewed evidence' \
  --finding FINGERPRINT --reviewer agent:codex
```

`--seed` resolves the current graph and creates only `observed` records with `provenance_baseline`.
It approves zero packages and copies no inherited trust list. `--list` is read-only. `--check`
reports missing, stale, revoked and discrepant reviews and exits 2 when any remain.

Review the findings, artifact bytes, context and coverage before recording a conclusion. A justified
false positive can be `cleared` by the agent with its evidence. `accepted_risk` requires
`--authorization` that references explicit user authorization already in the invocation or session.
Do not invent approval or ask again when authorization already exists. Without authorization,
preserve the unresolved risk. Reviewer defaults to `agent:codex`; never use Git identity to sign an
agent review as the user.

Criteria are `safe_to_run` for dev/test, `safe_to_deploy` for the reviewed production scope,
`does_not_implement_crypto` for that subcondition, and `provenance_baseline` for inventory only.
None promises absolute safety. `observed`, `rejected` and `revoked` never clear findings.

A decision applies only to its exact source/name/version/integrity/patch identity, matching
criterion, specific fingerprint and unchanged evidence. Empty fingerprints clear nothing. New
versions and new findings require review; reviews expire after 90 days. Local rejection/revocation
beats imported approval. Original findings and severity remain in the report.

The executable copies durable report evidence into `.claude/deps-audit/evidence/`, uses a file lock
and atomic replace, makes identical records a no-op, and preserves revision history. Commit ledger
and evidence together after verification. See [schema and
imports](references/ledger.md).

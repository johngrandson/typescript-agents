# Review Agent Spawning Reference

Detailed tables and prompt templates for spawning review specialists.
Referenced by `/ts:review` Step 2.

## Agent Selection Table

| Agent | subagent_type | When to spawn |
|-------|---------------|---------------|
| TypeScript Reviewer | `ts:typescript-reviewer` | **Always** |
| Iron Law Judge | `ts:iron-law-judge` | >200 lines changed AND access boundaries, React or job code in diff; skip only if the same checks already have current evidence |
| Verification Runner | `ts:verification-runner` | Affected package checks have not run for this diff; skip if `/ts:work` just passed all required verification tiers |
| Security Analyzer | `ts:security-analyzer` | Validation, session routes, streams, storage paths, secrets or proposed identity boundaries changed |
| Testing Reviewer | `ts:testing-reviewer` | Test files changed OR new public functions |
| Postgres jobs Specialist | `ts:background-jobs-specialist` | `apps/worker/src` or job repositories/contracts in `packages/db/src` changed |
| Deploy Validator | `ts:deployment-validator` | Dockerfiles, Compose configuration, deployment scripts or environment handling changed |
| Requirements Verifier | `ts:requirements-verifier` | Task ID detected OR plan/spec path passed (Step 1c succeeded). **Skip** on `--no-requirements` |
| Codex Reviewer | `ts:codex-reviewer` | **ONLY when `--codex` passed** — never in default selection. Does not count toward the max-5 cap |

Min 1, max 5 agents. For <200 lines changed: spawn only typescript-reviewer +
security-analyzer when the security boundaries above are affected. Hook
warnings are lexical checks and cannot establish a complete semantic review.

## Output File Mapping

Every agent prompt MUST include an explicit `output_file` path.

| Agent | output_file |
|-------|-------------|
| typescript-reviewer | `.claude/plans/{slug}/reviews/typescript.md` |
| testing-reviewer | `.claude/plans/{slug}/reviews/testing.md` |
| iron-law-judge | `.claude/plans/{slug}/reviews/iron-laws.md` |
| security-analyzer | `.claude/plans/{slug}/reviews/security.md` |
| background-jobs-specialist | `.claude/plans/{slug}/reviews/jobs.md` |
| deployment-validator | `.claude/plans/{slug}/reviews/deploy.md` |
| verification-runner | `.claude/plans/{slug}/reviews/verification.md` |
| requirements-verifier | `.claude/plans/{slug}/reviews/requirements.md` |
| codex-reviewer | `.claude/plans/{slug}/reviews/codex.md` |

## Standard Prompt Block

Include this instruction block in every agent prompt:

```
output_file: .claude/plans/{slug}/reviews/{agent}.md

CRITICAL: Write your findings to the output_file above. By turn ~12 at the
latest, call Write with whatever you have — partial is better than nothing
if you hit the turn limit. Continue analyzing and Write again to overwrite
with the full version. Your chat response body must be ≤300 words — the
file IS the real output.
```

## Codex Reviewer Prompt Block (`--codex` only)

Spawn `ts:codex-reviewer` in the SAME parallel batch as the
other agents with this prompt (plus the Standard Prompt Block above):

```
Run a Codex CLI review of this diff and normalize the findings.

base_branch: {default branch, e.g. main}
diff_files: {git diff --name-only output}
output_file: .claude/plans/{slug}/reviews/codex.md

Preflight `command -v codex` first. If codex is missing or the review
fails, write output_file with a SKIPPED note and stop — NEVER error.
Do not pass custom instructions with --base (CLI rejects it); the rubric
comes from the project's AGENTS.md "Review guidelines" section.
Normalize P0/P1→BLOCKER, P2→WARNING, P3→SUGGESTION. Tag every finding
with source [codex].
```

The codex review takes 1–5+ minutes — spawn it FIRST in the batch so it
overlaps the Claude agents. In Step 3b, mark issues flagged by both a
Claude agent and `[codex]` as HIGH CONFIDENCE (cross-model consensus).

## Focused Review Mode

When the user passes a focus argument, spawn only the specified agent:

| Argument | subagent_type |
|----------|---------------|
| `test` | `ts:testing-reviewer` |
| `security` | `ts:security-analyzer` |
| `jobs` | `ts:background-jobs-specialist` |
| `deploy` | `ts:deployment-validator` |
| `iron-laws` | `ts:iron-law-judge` |

Zero agents spawned = skill failure.

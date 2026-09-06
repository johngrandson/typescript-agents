# Pi Review Execution Reference

`/skill:ts-review` works without separately installed custom agents. Native Pi
subagents are an optional performance optimization, not a correctness dependency.

## Concern Selection

| Concern | Select when |
|---|---|
| TypeScript starter | Always |
| Security | Auth, session, password, token, upload, or input code changed |
| Testing | Tests changed, public behavior changed, or regression coverage is absent |
| Drizzle/React | Relevant schemas, queries, migrations, hooks, or components changed |
| worker | Worker or queue code changed |
| Deployment | Dockerfile, deployment scripts, environment, or runtime configuration changed |
| Requirements | A plan, specification, or issue is available |

## Parallel Mode

When native subagent tooling is available, delegate independent concerns to
generic read-only workers. Give each worker the same base ref, changed-file list,
requirements context, and instruction to return evidence-backed findings with
`path:line` citations. Keep one worker per concern and deduplicate in the parent.

When subagents are unavailable, expensive, or unnecessary, review the same
concerns sequentially in the current session. Never treat a sequential run as a
failed review and never require plugin-root agent definitions or Claude task APIs.

## Output Contract

Return findings to the current session. Do not write files unless the user asks
for a persisted report. The review remains read-only and ends after the verdict.

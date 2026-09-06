# Workflow state

`plan-stop-reminder.sh` handles a new Write to `.claude/plans/<slug>/plan.md`.
Known overwrite/update events are excluded. A sibling `progress.md` containing
`**State**:` identifies full mode and suppresses the planning reminder. For
planning-only scope, present the result; execution already authorized continues
within that scope. The reminder never adds an approval checkpoint.

`precompact-rules.sh` preserves planning, work or full state using the existing
files. It retains retries/cycle limits, relevant Dead Ends and authorization,
and reminds the agent to use scoped real pnpm/Turbo checks and `pnpm verify`
before claiming completion. `postcompact-verify.sh` requests rereading the first
pending plan and scratchpad. Neither executes checks, advances a phase nor grants
permission to take over another plan. Multiple plans retain the documented
modification-order/file-order selection limitations.

`log-progress.sh` writes JSONL edit metrics only under existing persistent
`${CLAUDE_PLUGIN_DATA}/skill-metrics/edits-YYYY-MM.jsonl`. Fields are timestamp,
relative file, project and identified package. Quotes/spaces are serialized as
JSON data. Root files have no invented package. It never writes plan progress or
creates an alternate metrics destination.

`check-pending-plans.sh` is silent without session background tasks or crons. With
those signals it emits counts and supporting pending-plan/uncommitted-change
context through `systemMessage`, with exit zero so stopping remains normal.
`stop_hook_active` suppresses the reminder. `stop-failure-log.sh` persists only a
short API-failure breadcrumb in the selected scratchpad for the next session.

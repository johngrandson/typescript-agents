# Concern Track Selection

Select research by feature concerns, not named agents.

| Feature type | Required concern tracks |
|---|---|
| CRUD or data-heavy | Existing patterns, Drizzle/data design |
| Interactive or real-time UI | Existing patterns, React architecture |
| External integration | Existing patterns, service boundaries; library evaluation only for a new dependency |
| Background processing | Existing patterns, worker behavior, Node shutdown and error propagation |
| Authentication/permissions | Existing patterns, security and negative paths |
| Refactoring/signature changes | Existing patterns, call-site tracing |

Run selected tracks sequentially in the current session by default. Native
generic workers are optional only for independent tracks.

## Dependency Research

Evaluate libraries only when adding a dependency absent from `package.json` or
comparing replacements. For an existing dependency, inspect `deps/{library}`
and its installed/version-matched documentation. Optional local dependency
documentation tools may be used only when independently configured and exposed.

## External Research

Use primary documentation and focused web research for unfamiliar technology,
known issues, or infrastructure questions. Capture URLs, findings, alternatives,
and confidence in `.claude/plans/{slug}/research/`.

## Clarification

Ask at most three focused questions when scope, integration points, performance,
or competing valid approaches cannot be resolved from repository evidence.

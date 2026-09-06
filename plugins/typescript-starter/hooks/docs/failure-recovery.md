# Failure recovery

`typescript-failure-hints.sh` classifies pnpm/Turbo, TypeScript, builds, Vitest,
lint/format and Drizzle failures. It identifies the affected package/filter and
first diagnostic identifiers, then requests a scoped investigation. Drizzle
hints inspect schema, SQLSTATE and migration state with disposable Postgres
coverage when appropriate. They never recommend reset as routine recovery.

`error-critic.sh` keys a failure sequence by canonical workspace, session, cwd
and literal command arguments including package/filter. Root web and mobile
filters therefore do not share a counter. State paths hash session identifiers
under an owner-specific temporary `typescript-starter` directory. Symlinked
state directories/files are rejected; updates use a file lock.

The first failure is silent. The second warns about repetition. The third
requires stopping the same approach, documenting failures, researching
alternatives and revisiting the approach through `/ts:investigate` or existing
solutions. There is no automatic fourth retry. The last five entries retain
only class, package and up to 18 sanitized diagnostic identifiers each, within
100 lines of consolidated evidence. Raw commands, env values, SQL parameters
and complete error messages are not persisted.

`stop-failure-log.sh` records only an API-interruption note and
`/ts:work --continue` in the selected scratchpad. It never stores the event's
sensitive error contents. Selection follows plan-directory modification time;
with multiple active plans that heuristic does not grant task authorization.

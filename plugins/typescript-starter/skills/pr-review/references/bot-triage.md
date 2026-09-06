# Bot Review Triage

CI bots (Copilot, Codex, CodeRabbit, SonarCloud) post review passes as
inline review threads + a review summary. They produce volume — triage in
batch, but never bulk-resolve without replies (SKILL.md Iron Laws 6 + 9).

## Known bot logins

`copilot-*`, `codex`, `coderabbitai`, `sonarcloud`, `github-actions`,
`dependabot`, `*-ci`. Detect via `__typename == "Bot"` (GraphQL) or
`user.type == "Bot"` (REST) — see `gh-commands.md` for why the `[bot]`
login suffix is unreliable.

## Batch flow (`--bots-only`)

1. Fetch unresolved threads, filter `isBot == true`
2. Classify each finding:

| Verdict | Signal | Action |
|---------|--------|--------|
| **Real bug** | Reproducible, matches code behavior | Fix → reply with diff summary → resolve |
| **Real but deferred** | Valid, out of this PR's scope | Reply "tracked as follow-up: {ref}" → resolve |
| **False positive** | Bot misread the code | Reply with one-line explanation of why it's safe → resolve |
| **Iron Law conflict** | Bot suggests an Iron Law violation | Reply declining with the law + reasoning → resolve |

3. Present the verdict table to the user BEFORE posting anything
4. Post replies + resolve only after approval

## Codex thread anatomy (chatgpt-codex-connector)

Codex inline comments have a fixed shape — parse it, don't guess:

- Priority badge: `![P1 Badge](https://img.shields.io/badge/P1-orange...)`
  (P1 orange / P2 yellow / P3), then a **bold one-line title**, a detailed
  body, and a `Useful? React with 👍 / 👎.` footer.
- Mapping: P0/P1 → investigate as a potential blocker; P2 → verify-then-fix;
  P3 → suggestion. Confirm the trigger, impact and current code before
  accepting the priority. A badge alone does not establish a defect.
- Reviews are per-commit (`Reviewed commit: <sha>` in the summary body) —
  after a force-push or big rebase, outdated codex threads are expected;
  handle via the standard outdated-thread rule.
- Reply + resolve works exactly like human threads. An optional reaction
  does not replace the reply or evidence for the verdict.
- With zero inline threads, inspect the summary for findings and the
  reviewed commit. Report a clean pass only when a completed review
  explicitly covers the current head and reports no outstanding issues.
  A reaction or an empty thread list alone does not establish that result.

## Common false-positive patterns (TypeScript)

- **Optional access flagged as a null dereference.** `value?.key` returns
  `undefined` for a nullish receiver. Direct `value[key]` throws on `null`
  or `undefined`, so verify the exact expression before dismissing a report.
  `value?.key ?? fallback` preserves `0` and `false`; `||` does not.
- **Type-only imports flagged as browser database code.** Check whether
  the import is erased and whether its module is allowed by the package
  boundary. `import type` from `@starter/types` carries no runtime code.
  A runtime import from `@starter/db` in a web client remains a real defect.
- **Expected API errors flagged as unhandled.** Trace an awaited `AppError`
  through the existing Fastify error handler and `toErrorResponse` before
  asking for a local catch. A detached rejecting promise is different:
  it needs an explicit owner and failure handling. Do not assume Node
  restarts failed work or isolates an error to one request.
- **Type annotations treated as input validation.** JSON parsing and an
  `as` assertion do not validate a payload. Keep shared TypeBox validators
  at REST, stream and persisted-data boundaries. A valid session UUID or
  stream `clientId` identifies data or a connection; it does not prove
  the caller is authorized to act on it.

## What NOT to do

- Never auto-resolve a bot pass to "clean up the PR" — each thread gets a
  reply first, even one line.
- Never accept a bot's code suggestion verbatim without reading the
  surrounding code — bots see the diff hunk, not the module.
- Never let a bot summary (review body) block on "resolution" — summaries
  are not threads and cannot be resolved; address inline findings instead.

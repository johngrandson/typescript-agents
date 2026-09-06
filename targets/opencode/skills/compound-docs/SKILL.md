---
name: compound-docs
description: Use when searching verified TypeScript/Fastify/Drizzle solution docs
  by symptom, component or root cause before a repeated investigation.
---

# Compound solution documents

Store verified lessons under `.claude/solutions/{category}/{slug}.md` with YAML frontmatter. Categories include contracts, api, database, web, mobile, realtime, jobs, runtime,
testing, deployment and dependencies.

## Usage

```text
rg -n "stale-response|ownership" .claude/solutions
rg -n "SessionService|archive" .claude/solutions
```

## Required solution fields

`title`, `date`, `component`, `problem_type`, `severity`, `symptoms`, `root_cause`, `resolution`, `tags`, plus relevant affected files and verification evidence. Record exact
dependency versions/integrities for supply-chain or library behavior claims. Evidence dates and source paths distinguish current behavior from historical solutions.

## Search and reuse

Search symptom phrases, symbols, workspace paths and tags with rg. Read the closest matches and confirm their source still applies before reusing a fix. A prior solution is
evidence to investigate, not a guarantee the current cause is identical.

## Example

A stale mobile load can overwrite a newly selected session. Record the screen hook, request-ownership condition, reproduction and its regression test; tag it mobile, stale-response
and ownership. Do not write an unverified code recipe or duplicate an existing solution when one update preserves the history.

Use `/ts-compound` to capture a solved problem, `/ts-recall` for session/Git history and `/ts-learn-from-fix` for a short rule. Preserve frontmatter schema and resolution sections
described in the references.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

## References

- [Resolution template](references/resolution-template.md)
- [Schema](references/schema.md)

# Review Conventions System

After a review, users can mark findings as accepted patterns (suppress
in future reviews) or new conventions (enforce in future reviews).
This prevents repeat noise and compounds review knowledge.

## Convention File

Location: `.claude/conventions.md` (project root, checked into git)

### Entry Format

```markdown
## Convention C{ID}: {Title}

- **Type**: SUPPRESS | ENFORCE
- **Source**: Review of {feature} on {date}
- **Pattern**: {code pattern or description}
- **Rationale**: {why this is accepted/required}
```

### Example Entries

```markdown
## Convention C001: Shared type imports in browser code

- **Type**: SUPPRESS
- **Source**: Review of {web client change} on {date}
- **Pattern**: An `import type` from `@starter/types` used in a web client
- **Rationale**: Type-only imports are erased. This exception does not permit
  runtime imports from `@starter/db` or access to server secrets.

## Convention C002: API routes preserve shared validation and error envelopes

- **Type**: ENFORCE
- **Source**: Review of {API route change} on {date}
- **Pattern**: Keep the shared TypeBox schemas at route boundaries and return
  failures through the existing `toErrorResponse` mapping.
- **Rationale**: Type assertions do not validate requests, and raw driver
  errors can expose SQL or bound values. This convention does not establish
  authentication or make a session identifier an authorization check.
```

## How Review Agents Use Conventions

At review start, if `.claude/conventions.md` exists:

1. Read the file
2. **SUPPRESS** entries: Skip findings that match the pattern. Do NOT
   report them as issues — they are intentionally accepted.
3. **ENFORCE** entries: Flag violations of enforced patterns as WARNINGS.
   These are project-specific rules beyond Iron Laws.

## Interactive Extraction Flow

After presenting review findings (Step 5), offer:

```
Any findings to convert to conventions?
- SUPPRESS: "We do this intentionally, stop flagging it"
- ENFORCE: "This should always be done this way going forward"
- Skip: No conventions to add
```

For each accepted convention:

1. Assign next sequential ID (C001, C002, ...)
2. Write to `.claude/conventions.md`
3. Attribute to the review that surfaced it

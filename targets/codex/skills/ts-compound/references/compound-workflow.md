# Compound workflow

## The Compounding Effect

```
Cycle 1: Fix bug → Document solution
Cycle 2: Hit similar bug → Find solution in docs → Fix faster
Cycle 3: Agent finds solution → Prevents bug before it ships
```

Record the symptom, root cause and verified fix so later investigations can
find the relevant evidence by module and failure mode.

## Detailed Workflow

### Phase 1: Context Detection

#### From Arguments

```
$typescript-starter:ts-compound Fixed repeated session queries in SessionService.list by using the repository list projection
```

Extract: module=SessionService, symptom=repeated SQL, root_cause=findById inside the list loop.

#### From Session Context

Check these sources in order:

1. **Scratchpad DEAD-END and DECISION entries**:

   ```bash
   grep -A 5 "DEAD-END\|DECISION" .claude/plans/*/scratchpad.md 2>/dev/null | tail -20
   ```

2. **Recent git changes**:

   ```bash
   git log --oneline -5
   git diff HEAD~1 --stat
   ```

3. **Progress file completions**:

   ```bash
   ls -t .claude/plans/*/progress.md 2>/dev/null | head -1
   ```

#### Trivial Fix Filter

Skip documentation for:

- Typo fixes (single character changes)
- Import/alias additions
- Config value changes
- Formatting-only changes
- Changes to fewer than 3 lines with no investigation

### Phase 2: Duplicate Detection

Search existing solutions before creating new:

```bash
rg -l "timeout|repeated SQL|N\+1" .claude/solutions/
rg -l 'module: "SessionService"' .claude/solutions/
```

If match found, read the file and compare:

- **Same root cause + same module**: Update existing (add new symptom)
- **Same root cause + different module**: Create new with cross-reference
- **Different root cause**: Create new (different problem)

### Phase 3: Information Gathering

```yaml
module: "SessionService"
date: "{YYYY-MM-DD}"
problem_type: runtime_error
component: drizzle_query
symptoms:
  - "Repeated SQL query per listed session"
root_cause: "Repeated findById in a session-list loop"
severity: medium
tags: [batch-query, session-list, n-plus-one]
```

Gathering strategy:

1. Check session context first (scratchpad, git diff, progress)
2. Fill what you can automatically
3. Ask user ONLY for missing critical fields

### Phase 4: Schema Validation

Validate frontmatter against `../../compound-docs/references/schema.md`.
Use suggested values when they fit; create descriptive labels when
they don't. Only `severity` is a strict enum.

### Phase 5: File Creation

Create in `.claude/solutions/{category}/` using the template from
`../../compound-docs/references/resolution-template.md`.

Filename: `{sanitized-symptom}-{module}-{YYYYMMDD}.md`

### Phase 6: Cross-Referencing

After creating the solution file:

1. Search for related solutions by tags
2. Add `related_solutions` to new file if matches found
3. Update related files to reference new solution

### Phase 7: Promotion Check

If the solution matches any of these, suggest promotion:

- **severity: critical** — Suggest adding to Iron Law checks
- **Iron Law violation** — Suggest updating iron-law-judge
- **Recurring pattern** (3+ similar) — Suggest adding to skill reference

## Integration with Other Skills

- `$typescript-starter:ts-learn-from-fix` captures quick patterns in `common-mistakes.md`
- `$typescript-starter:ts-compound` captures detailed solutions with full context
- `$typescript-starter:ts-investigate` searches `.claude/solutions/` before investigating
- `$typescript-starter:ts-plan` consults for known risks in planned areas

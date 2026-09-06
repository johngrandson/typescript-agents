---
name: ts-compound
description: Use after a verified fix to capture a searchable TypeScript starter solution
  with root cause…
---

# Compound — Capture Solutions as Knowledge

After fixing a problem, capture the solution as searchable
institutional documentation.

## Usage

```
$typescript-starter:ts-compound Fixed N+1 query in user listing
$typescript-starter:ts-compound Resolved React timeout in dashboard
$typescript-starter:ts-compound   # Auto-detects from recent session context
```

## Philosophy

> Each unit of engineering work should make subsequent units
> easier — not harder.

## Workflow

### Step 1: Detect Context

1. If `$ARGUMENTS` provided, use as description
2. If no args, check scratchpad DEAD-END/DECISION entries,
   `git diff`, `.claude/plans/{slug}/progress.md` for recent completions
3. If unclear, ask: "What problem did you just solve?"

**Only document non-trivial problems** that required investigation.

### Step 2: Search Existing Solutions

Create `.claude/solutions/` directory if it doesn't exist (run `mkdir -p .claude/solutions`).
Then search `.claude/solutions/` for relevant keywords using Grep.

If found: **Create new** (different root cause), **Update
existing** (same root cause, new symptom), or **Skip**.

### Step 3: Gather Details and Create Solution

Extract from session context: module, symptoms, investigation
steps, root cause, solution code, and prevention advice.

Validate frontmatter against `../compound-docs/references/schema.md`,
then create file using `../compound-docs/references/resolution-template.md`.

**Write-blocked fallback**: if writing to `.claude/solutions/` is denied
by permissions, do NOT silently drop the solution. Output the full
solution doc inline (fenced markdown the user can paste), then suggest
`$typescript-starter:ts-permissions` to allow `.claude/solutions/` writes for next time.

### Step 4: Decision Menu

1. **Continue** (default)
2. **Promote to Iron Law check** — Add to iron-law-judge
3. **Update skill reference** — Add to relevant skill
4. **Update CLAUDE.md** — Add prevention rule

## Auto-Trigger Phrases

When user says "that worked", "it's fixed", "problem solved",
"the fix was" — suggest `$typescript-starter:ts-compound`.

### Supply-chain finding auto-feed (Phase 3)

When `$typescript-starter:ts-deps-audit` produces a BLOCK-severity finding that the
user investigates and confirms is a real malicious pattern (not a
false positive), suggest:

> Caught a high-severity finding in `<pkg>@<version>`. Run
> `$typescript-starter:ts-compound` to capture this for future audits?

If accepted, the resulting solution doc goes to
`.claude/solutions/supply-chain/<pkg>-<cve_or_pattern>.md` and
includes the exact rule-id + snippet + diff window that triggered
the finding. This compounds the audit corpus: future runs of
`$typescript-starter:ts-deps-audit` grep `solutions/supply-chain/` for snippet
matches and pre-elevate severity on known-bad patterns.

**Always prompt; never auto-write.** Solution docs are durable and
shape future trust calls — the user reviews before committing.

## Iron Laws

1. **YAML frontmatter validates or STOP**
2. **Symptoms must be specific** — not "it broke"
3. **Root cause is WHY, not WHAT**
4. **One problem per file**
5. **NEVER document a fix before verifying it works** — run `pnpm check-types && pnpm test:run` first; unverified solutions poison the knowledge base

## Integration with Workflow

```text
$typescript-starter:ts-review → Complete → $typescript-starter:ts-compound  ← YOU ARE HERE
                              │
                 .claude/solutions/{category}/{fix}.md
                              │
              $typescript-starter:ts-investigate and $typescript-starter:ts-plan search here
```

## References

- `references/compound-workflow.md` — Detailed step-by-step
- See also: `compound-docs` skill for schema and templates

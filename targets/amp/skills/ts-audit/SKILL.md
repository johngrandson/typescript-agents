---
name: ts-audit
description: Use when assessing TypeScript starter health across architecture, performance,
  security, tests and dependencies; supports quick, full, focused and incremental
  audits.
---

# Project Health Audit

Comprehensive project-wide health assessment across five independent concern tracks.

## Usage

```
ts-audit              # Full audit (default)
ts-audit --quick      # 2-3 minute pulse check
ts-audit --focus=security   # Deep dive single area
ts-audit --focus=performance
ts-audit --since abc123   # Incremental audit since commit
ts-audit --since HEAD~10  # Audit last 10 commits
```

## When to Use

- **Quarterly** health checks
- **Before major releases**
- **After large refactors**
- **New team member onboarding** (understand codebase health)

## Iron Laws

1. **Complete every selected track before synthesizing** — partial results make
   cross-category scores misleading
2. **Scope each track to concrete directories and checks** — vague project-wide
   analysis produces generic findings
3. **Never compare scores across projects** — track trends only within the same
   codebase
4. **Run quick mode before full mode** — catch basic failures before expensive
   analysis

## Portable Audit Workflow

1. Create `.claude/audit/reports/` and `.claude/audit/summaries/`.
2. Run the quick checks below. Stop and report a blocker when the project cannot
   compile or its test command cannot start.
3. Complete five tracks: architecture, performance, security, tests, and
   dependencies. Native generic workers may run independent tracks in parallel
   when the runtime provides them; otherwise run every track sequentially in
   this session. Never require named custom agents.
4. Write one evidence-focused report per track under `.claude/audit/reports/`.
   Report issues only, cite paths and lines, and use one summary line for a
   clean area.
5. After all selected reports exist, deduplicate findings, identify
   cross-category correlations, calculate scores using
   `references/scoring-methodology.md`, and write
   `.claude/audit/summaries/project-health-{date}.md`.

If two or more optional workers fail or hit limits, finish the missing tracks
sequentially. Never present an incomplete track as audited.

## Output Format

Report an executive health score, per-category scores for Architecture,
Performance, Security, Tests, and Dependencies, critical issues, top
recommendations, and an Immediate/Short-term/Long-term action plan.

## Quick Mode (`--quick`)

Only run essential checks (~2-3 minutes):

Run `pnpm check-types`, then `pnpm audit --json`,
then `pnpm knip` and `pnpm test:run`. Save raw output and preserve every exit code; summarize only after completion.

Skip: Full security scan, N+1 analysis, test quality metrics, architecture deep dive.

## Focus Mode (`--focus=area`)

Run only the selected concern track with its deeper checks:

| Focus | Extra checks |
|-------|--------------|
| `security` | Full OWASP review, security review, manual authorization patterns |
| `performance` | Query plans, N+1 inventory, profiling evidence |
| `architecture` | Workspace dependency graph, coupling matrix, cohesion |
| `tests` | Coverage by context, isolation, flaky-test indicators |
| `deps` | Vulnerabilities, licenses, maintenance status |

## Incremental Mode (`--since <commit>`)

Analyze only changes since a specific commit. Useful for pre-merge checks:

Run `git diff --name-only <commit>...HEAD` to identify changed files, then run targeted audits on changed files only (skips full project scan).

Combines with other flags: `ts-audit --since HEAD~5 --focus=security`

## Relationship to Other Commands

| Command | Scope | Frequency |
|---------|-------|-----------|
| `ts-review` | Changed files (diff) | Every PR |
| `ts-audit` | Entire project | Quarterly |
| `ts-boundaries` | Context structure | On-demand |
| `ts-verify` | Compile/test pass | Anytime |

## References

- `references/scoring-methodology.md` - How scores are calculated
- `references/architecture-checks.md` - Detailed architecture criteria

---
name: audit
description: Use when assessing TypeScript starter health across architecture, performance, security, tests and dependencies; supports quick, full, focused and incremental audits.
effort: high
argument-hint: '[--quick|--full|--focus=area|--since=commit]'
---

# Project Health Audit

Comprehensive project-wide health assessment using 5 parallel specialist subagents.

## Usage

```
/ts:audit              # Full audit (default)
/ts:audit --quick      # 2-3 minute pulse check
/ts:audit --focus=security   # Deep dive single area
/ts:audit --focus=performance
/ts:audit --since abc123   # Incremental audit since commit
/ts:audit --since HEAD~10  # Audit last 10 commits
```

## When to Use

- **Quarterly** health checks
- **Before major releases**
- **After large refactors**
- **New team member onboarding** (understand codebase health)

## Iron Laws

1. **Wait for ALL agents before synthesizing** — Partial results create misleading health scores because cross-category correlations get missed
2. **Scope agent prompts to specific directories** — Vague prompts like "analyze the codebase" produce generic findings that waste tokens and miss real issues
3. **Never compare scores across projects** — Scoring methodology depends on project size and maturity; only track trends within the same project
4. **Quick mode before full mode** — Run `--quick` first to catch compile/test failures before spending tokens on 5 parallel agents

## Subagent Architecture

Spawn 5 specialists in parallel using Agent tool. Each call routes to a
declared-model plugin specialist (sonnet/opus) so the work doesn't fall
through to `general-purpose` (Opus by default):

| Subagent | Focus | Output File | Routes to |
|----------|-------|-------------|-----------|
| Architecture Reviewer | Structure quality, coupling, cohesion | `arch-review.md` | `starter-patterns-analyst` (sonnet) |
| Performance Auditor | N+1, indexes, bottlenecks, scalability | `perf-audit.md` | `general-purpose` (TODO: no perf specialist exists yet) |
| Security Auditor | OWASP scan, auth patterns, secrets | `security-audit.md` | `security-analyzer` (opus) |
| Test Health Auditor | Coverage, quality, flaky tests | `test-audit.md` | `testing-reviewer` (sonnet) |
| Dependency Auditor | Vulnerabilities, outdated, unused | `deps-audit.md` | `general-purpose` (TODO: per-package `npm-deps-triager` only) |

## Workflow

### Step 1: Create Task List and Spawn All 5 Auditors (Parallel)

**Create Claude Code tasks** for real-time progress visibility:

```
For each auditor:
  TaskCreate({subject: "{Area} audit", activeForm: "Auditing {area}..."})
  TaskUpdate({taskId, status: "in_progress"})
```

Then spawn all 5 agents with Agent tool (parallel). Route to declared-model
specialists where they exist, keep `general-purpose` only where no specialist
covers the audit category:

```
Agent(subagent_type: "ts:starter-patterns-analyst", prompt: "Architecture audit: analyze module structure, context boundaries, coupling, cohesion. Write findings to .claude/audit/reports/arch-review.md", run_in_background: true)
Agent(subagent_type: "general-purpose",          prompt: "Performance audit: N+1 queries, missing indexes, bottlenecks, scalability. Write findings to .claude/audit/reports/perf-audit.md", run_in_background: true)
Agent(subagent_type: "ts:security-analyzer",        prompt: "Security audit: OWASP scan, auth patterns, secret leakage. Write findings to .claude/audit/reports/security-audit.md", run_in_background: true)
Agent(subagent_type: "ts:testing-reviewer",         prompt: "Test health audit: coverage, quality, flakes. Write findings to .claude/audit/reports/test-audit.md", run_in_background: true)
Agent(subagent_type: "general-purpose",          prompt: "Dependency audit: vulnerabilities, outdated, unused. Write findings to .claude/audit/reports/deps-audit.md", run_in_background: true)
```

**Why specialist routing matters**: `general-purpose` subagents inherit the
parent session model (usually Opus). Plugin specialists declare their own
model in frontmatter (sonnet/haiku for most). Routing 3 of 5 audit tracks to
declared-model specialists materially cuts Opus subagent volume per audit run.

**Agent prompts must be FOCUSED.** Scope each prompt to the
relevant directories and patterns. Do NOT give vague prompts
like "analyze the codebase."

**Output efficiency**: Tell each agent: "Report ONLY issues found.
Do NOT list clean checks, passing categories, or 'What's Good'.
One summary line per clean area suffices."

### Step 2: Collect Results

Wait for ALL auditors to complete. Mark each auditor's task as
`completed` via `TaskUpdate` as it finishes. NEVER proceed while
any auditor is still running.

Read reports from `.claude/audit/reports/`.

**Rate-limit circuit breaker:** if 2+ auditors return empty results or
rate-limit/API errors, STOP spawning. Synthesize from the reports that
exist, mark missing categories as "not audited (rate limit)", and tell
the user to re-run `/ts:audit` after the limit resets. Never leave the
user typing "continue" against dead agents.

### Step 3: Compress Findings

After all 5 auditors complete, spawn context-supervisor:

```
Agent(subagent_type: "ts:context-supervisor", prompt: """
Compress audit findings.
Input: .claude/audit/reports/
Output: .claude/audit/summaries/
Priority: Health scores per category, critical findings
only, cross-category correlations, deduplicate findings
found by 2+ agents.
""")
```

Read `.claude/audit/summaries/consolidated.md` for synthesis.

### Step 4: Calculate Health Score

Each category scores 0-100. See `${CLAUDE_SKILL_DIR}/references/scoring-methodology.md`.

### Step 5: Generate Report

Write to `.claude/audit/summaries/project-health-{date}.md`.

## Output Format

Report includes: Executive summary with health score (A-F, numeric/100),
per-category score table (Architecture, Performance, Security, Tests, Dependencies),
critical issues, top recommendations, and action plan (Immediate/Short-term/Long-term).

## Quick Mode (`--quick`)

Only run essential checks (~2-3 minutes):

Run `pnpm check-types`, then `pnpm audit --json`,
then `pnpm knip` and `pnpm test:run`. Save raw output and preserve every exit code; summarize only after completion.

Skip: Full security scan, N+1 analysis, test quality metrics, architecture deep dive.

## Focus Mode (`--focus=area`)

Deep dive single area with full specialist resources:

| Focus | Subagent | Extra Checks |
|-------|----------|--------------|
| `security` | security-analyzer | OWASP review, dependency advisories, source inspection |
| `performance` | general-purpose | Profile-level analysis, query explain (no plugin specialist yet) |
| `architecture` | starter-patterns-analyst | Import graph, coupling matrix, cohesion |
| `tests` | testing-reviewer | Coverage by context, quality metrics |
| `deps` | general-purpose | License audit, maintenance status (per-package `npm-deps-triager` only) |

## Incremental Mode (`--since <commit>`)

Analyze only changes since a specific commit. Useful for pre-merge checks:

Run `git diff --name-only <commit>...HEAD` to identify changed files, then run targeted audits on changed files only (skips full project scan).

Combines with other flags: `/ts:audit --since HEAD~5 --focus=security`

## Relationship to Other Commands

| Command | Scope | Frequency |
|---------|-------|-----------|
| `/ts:review` | Changed files (diff) | Every PR |
| `/ts:audit` | Entire project | Quarterly |
| `/ts:boundaries` | Context structure | On-demand |
| `/ts:verify` | Compile/test pass | Anytime |

## References

- `${CLAUDE_SKILL_DIR}/references/scoring-methodology.md` - How scores are calculated
- `${CLAUDE_SKILL_DIR}/references/architecture-checks.md` - Detailed architecture criteria

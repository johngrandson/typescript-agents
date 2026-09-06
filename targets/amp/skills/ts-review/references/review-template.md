# Review Template Format

## Full Review Template

Write to `.claude/plans/{slug}/reviews/{feature}-review.md`:

```markdown
# Review: {Feature or Scope}

**Date**: {date}
**Files Reviewed**: {count}
**Reviewers**: typescript-reviewer, testing-reviewer, security-analyzer

## Summary

| Severity | Count |
|----------|-------|
| Blockers | {n} |
| Warnings | {n} |
| Suggestions | {n} |

**Verdict**: PASS | PASS WITH WARNINGS | REQUIRES CHANGES | BLOCKED

## Requirements Coverage (from {REQUIREMENTS_SOURCE})

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | {requirement text, ~80 chars} | MET | `apps/api/src/modules/sessions/service.ts:42` |
| 2 | {...} | PARTIAL | handler at `{actual route path}:{line}`; no test for error branch |
| 3 | {...} | UNMET | not found in diff |
| 4 | {...} | UNCLEAR | UX requirement — manual verification needed |

**Summary**: {n_met} MET · {n_partial} PARTIAL · {n_unmet} UNMET · {n_unclear} UNCLEAR

*Omit this entire section if `--no-requirements` was passed. If detection
failed, replace the table with a single line: `**NOT AVAILABLE** —
{reason}`. Placement is intentional: this block precedes the per-severity
findings because "did we deliver what we promised" is the user's first
question.*

## Blockers ({n})

### 1. {Issue Title}

**File**: {path}:{line}
**Reviewer**: {agent}
**Issue**: {description}
**Why this matters**: {impact explanation}

**Current code**:

```text
{verified TypeScript excerpt with source path and test evidence}
```

**Recommended approach**:

```text
{verified TypeScript excerpt with source path and test evidence}
```

---

### 2. {Issue Title}

...

## Warnings ({n})

### 1. {Issue Title}

**File**: {path}:{line}
**Reviewer**: {agent}
**Issue**: {description}
**Recommendation**: {what to do}

---

## Suggestions ({n})

### 1. {Suggestion Title}

**File**: {path}
**Suggestion**: {improvement idea}

---

## Next Steps

How would you like to proceed?

- `ts-plan` — Replan the fixes (for complex/architectural issues)
- `ts-work` — Fix directly (for simple, clear fixes)
- I'll handle it myself

```

## Verdict Decision Rules

| Verdict | Conditions |
|---------|-----------|
| **PASS** | No blockers, no warnings, suggestions only, all requirements MET |
| **PASS WITH WARNINGS** | No blockers, warnings present but not test-coverage gaps, OR some requirements PARTIAL |
| **REQUIRES CHANGES** | No Iron Law blockers but test coverage gaps detected (see below), OR any requirement UNMET |
| **BLOCKED** | Iron Law violations or critical security/data issues |

### REQUIRES CHANGES Triggers

This verdict catches code that works but lacks adequate test coverage:

- New public functions with zero tests
- Removed tests without replacement coverage
- New client interaction handlers without corresponding tests
- New worker handlers or runner transitions without execution, retry,
  lease or shutdown tests for the changed behavior
- New web/mobile views without relevant render and interaction tests

These are not blockers (code works) but should not merge without tests.

## Mandatory Summary Table

Every review MUST end with this at-a-glance table (even if only 1 finding):

| # | Finding | Severity | Reviewer | File | New? |
|---|---------|----------|----------|------|------|
| 1 | {title} | BLOCKER/WARNING/SUGGESTION | {agent} | {path}:{line} | Yes/Pre-existing |

**New?** column: "Yes" = finding on changed lines (this diff). "Pre-existing" = on unchanged code. Pre-existing issues appear in the report but do NOT affect the verdict.

**IMPORTANT**: The review template does NOT include task lists (`- [ ]`),
fix phases, or plan modifications. Review is findings-only. Task creation
belongs in `ts-plan`.

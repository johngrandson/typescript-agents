# Resolution Template

Use this template when creating solution documentation in `.claude/solutions/`.

## Filename Convention

```
{sanitized-symptom}-{module}-{YYYYMMDD}.md
```

- Lowercase, hyphen-separated
- Special characters removed
- Truncated under 80 characters
- Example: `stale-session-snapshot-mobile-store-20260905.md`

## Full Template

````markdown
---
module: "{TypeScript module, service or package}"
date: "{YYYY-MM-DD}"
problem_type: {concise category from schema suggestions or a new label}
component: {affected component label}
symptoms:
  - "{Observable symptom 1}"
  - "{Observable symptom 2}"
root_cause: "{specific cause established by evidence}"
severity: {critical|high|medium|low}
tags: [{tag1}, {tag2}, {tag3}]
---

# {Descriptive Title}

## Symptoms

What was observed. Include:
- Error messages (exact text)
- Unexpected behavior description
- Where it manifested (which component, service, worker or test)

## Investigation

What was tried and what happened:

1. **Hypothesis 1**: {what you thought} — {result}
2. **Hypothesis 2**: {what you thought} — {result}
3. **Root cause found**: {the actual cause}

## Root Cause

Detailed explanation of WHY this happened. Connect to the
underlying TypeScript starter concept.

```text
{verified TypeScript excerpt with source path and test evidence}
```

## Solution

The fix that resolved it.

```text
{verified TypeScript excerpt with source path and test evidence}
```

### Files Changed

- `apps/api/src/modules/sessions/service.ts:42` — Added batch query
- `apps/api/src/modules/sessions/__tests__/service.test.ts:15` — Added test for batch query

## Prevention

How to prevent this from recurring:

- [ ] Add to Iron Laws? (if foundational pattern)
- [ ] Add to agent checks? (if detectable by reviewer)
- [ ] Add to test patterns? (if testable)
- Specific guidance: "{actionable advice}"

## Related

- `.claude/solutions/{related-file}.md` — Similar issue in different context
- Iron Law #{n}: {description} (if applicable)
````

## Category Directories

Create the file in the appropriate subdirectory:

| problem_type | Directory |
|-------------|-----------|
| `build_error` | `build-issues/` |
| `test_failure` | `testing-issues/` |
| `runtime_error` | `api-issues/` |
| `performance_issue` | `performance-issues/` |
| `database_issue` | `database-issues/` |
| `security_issue` | `security-issues/` |
| `react_bug` | `react-issues/` |
| `job_issue` | `job-issues/` |
| `runtime_issue` | `runtime-issues/` |
| `integration_issue` | `api-issues/` |
| `logic_error` | `api-issues/` |
| `deployment_issue` | `deployment-issues/` |
| `iron_law_violation` | mapped by Iron Law domain |

## Quality Checklist

Before saving, verify:

- [ ] YAML frontmatter validates against schema
- [ ] Severity uses an allowed value; other labels accurately describe the issue
- [ ] Symptoms are specific (include error text)
- [ ] Root cause explains WHY, not just WHAT
- [ ] Solution includes code examples
- [ ] Prevention has actionable next steps
- [ ] File is in correct category directory

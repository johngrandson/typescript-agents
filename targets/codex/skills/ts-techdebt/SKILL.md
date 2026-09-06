---
name: ts-techdebt
description: Use when assessing duplicated contracts, leaky service/repository boundaries,
  unused…
---

# Technical debt assessment

Read the changed area and its consumers; this is an assessment, not automatic refactoring.

1. Run existing ESLint, TypeScript and Knip checks when permitted, retaining real failures. Do not equate an unused-export warning with a runtime defect.
2. Look for duplicated DTOs/runtime validation instead of shared TypeBox contracts, repeated event projection instead of applySessionEvent, HTTP logic in services or SQL in route/client layers.
3. Check app-to-app imports, worker dependence on API, stale docs and platform coupling. Services and repository ports are intended; do not classify them as needless wrappers.
4. Distinguish harmless repeated syntax from rules likely to diverge. Prefer a small extraction only when two consumers truly share semantics.
5. Rank findings by current cost, change risk and measurable benefit. Cite file/line, affected behavior, proposed boundary and tests.

Output a table of debt, evidence, impact, effort and recommendation. Use `$typescript-starter:ts-plan` for coordinated changes and `$typescript-starter:ts-quick` for contained fixes. Avoid adding
indirection simply to
reduce a duplicate-line count.

## Usage

```text
$typescript-starter:ts-techdebt
pnpm lint
pnpm knip
```

## Iron Laws

1. Cite current code and observable cost before proposing an abstraction.
2. Keep services and repository ports: they express the starter’s intended boundaries.
3. NEVER change source or weaken tests as part of this read-only assessment.

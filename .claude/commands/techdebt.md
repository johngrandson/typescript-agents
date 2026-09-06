---
name: techdebt
description: Find TypeScript starter technical debt across API, web, mobile, database and worker boundaries.
---

# Tech Debt Scanner

1. Read workspace manifests, `turbo.json`, shared ESLint config and the actual
   package dependency graph before choosing a scope.
2. Run `pnpm knip` for unused exports/dependencies and `pnpm check-types` for
   contract drift. Distinguish intentional entry points from dead code.
3. Inspect duplicated business logic between services and client components,
   unsafe casts at TypeBox boundaries, leaking database errors, and missing
   repository contract tests.
4. Check web Server Actions/BFF access separately from mobile REST/WS services;
   mobile effect loading is a valid architecture choice in this starter.
5. Check worker idempotency, lease fencing, retries, cancellation and shutdown.
6. Run focused tests before proposing a refactor; preserve public behavior.

## Iron Laws

- NEVER turn a stylistic preference into an unsupported project requirement.
- Trace each finding to `path:line`, an observed consequence and a proposed fix.
- Report priority and verification gaps; do not edit during a requested audit.

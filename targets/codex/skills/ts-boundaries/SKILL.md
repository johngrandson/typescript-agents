---
name: ts-boundaries
description: Use when analyzing TypeScript package imports, Fastify module coupling,
  repository ports…
---

# Package and module boundary validation

## Usage

`$typescript-starter:ts-boundaries [--assess|--fix]` inspects imports and contracts. `--assess` produces a scored health report; `--fix` produces concrete refactoring proposals, not automatic source
edits.

For an API/worker coupling check, locate actual dependency declarations and calls before assigning a violation:

```bash
rg -n '@starter/(api|worker)|SessionService' apps/worker packages
rg -n 'dependencies|exports|@starter/' apps/worker/package.json packages/db/package.json
```

## Analysis

1. Map package manifests, exports, TypeScript path aliases and imports with rg. Inspect the Turbo task graph and installed Knip config; Knip is not a complete call graph.
2. Trace incoming/outgoing dependencies of changed modules. Mark dynamic registry edges, callbacks and unresolved imports explicitly.
3. Check contracts in packages/types, domain behavior in services, storage behind repository ports and explicit AppContext/registry composition. Services and repository adapters are intentional.
4. Check app boundaries: worker must not import API; clients must not import server-only code; mobile must not use DOM components from packages/ui. Share pure projection and contracts across clients.
5. Identify cycles by actual runtime/build effect. Type-only cycles differ from initialization hazards. Verify consumers before proposing an extraction.

## Assessment

Score explicit, evidenced categories on a 0–100 scale: boundary integrity 30, dependency direction 25, cohesion 20, public contract clarity 15, verifiable isolation 10. Deduct only
observed violations; show per-category evidence and label uninspected areas UNKNOWN. Do not count missing information as healthy.

Report overall score, dependency graph, violations by severity, affected consumers and ranked refactoring proposals. Revalidate typechecks, package builds and behavior after an
authorized refactor. Never split a service solely to meet a line-count target. Use `$typescript-starter:ts-plan` for coordinated changes.

## Iron Laws

1. Verify imports, package exports and consumers before scoring a boundary violation; record unresolved dynamic edges.
2. Preserve services and repository adapters when they own domain behavior and storage isolation; assess cohesion by responsibility and evidence.
3. Keep web server-only imports, native mobile components and worker entry points within their actual runtime boundaries.
4. NEVER perform source edits in `--assess` or `--fix`; present the evidence and concrete refactoring proposal for the authorized implementation workflow.

## References

- [Context design](references/context-design.md)
- [Refactoring boundaries](references/refactoring-boundaries.md)

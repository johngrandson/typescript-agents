---
name: ts-verify
description: Use after TypeScript starter edits to verify workspace typechecks, ESLint,
  Vitest tests, schema…
---

# Verification loop

## Usage

```text
pnpm --filter @starter/types check-types
pnpm --filter @starter/types lint
pnpm --filter @starter/types test:run
pnpm verify
```

## Step 0: discover the project

Read `package.json`, `pnpm-workspace.yaml`, `turbo.json`, changed paths and local rules. Resolve the nearest workspace and actual package name. Run commands from the correct root
or with `pnpm --filter <package>`; do not assume every package has every script. Read [project discovery](references/project-discovery.md).

## Sequence

1. `check-types`: run affected workspace scripts and dependent workspaces when a shared export changes. Server builds and package typechecking differ; run builds when packaging/imports change.
2. `lint`: run the installed ESLint script; apply `lint:fix` only within the authorized change, then inspect the diff. Prettier/format settings come from the workspace; never
   invent a missing root format script.
3. `test:run`: execute affected existing Vitest suites, including contract consumers. Preserve failure exit codes and full logs even when summarizing output.
4. `pnpm verify`: final monorepo gate runs Turbo typecheck/lint/tests plus Knip. Knip finds unused exports/dependencies; it is not a complete call graph or correctness proof.
5. Conditional integration: `pnpm test:postgres` for database semantics/migrations/leases; `pnpm test:e2e` for browser flows; `pnpm test:deploy` for image/env/migration ordering.
   Inspect prerequisites before running. Mobile compatibility/export/device verification is a separate observation.

## Repair and reporting

Fix actual failures and rerun the failed gate plus checks affected by the fix. After 3 failed attempts, record what failed, investigate alternatives and stop blind retries. Do not
disable tests, hooks or typechecking, and do not reset a database.

Output a table of command, workspace, result, exit code and artifact/log. Use PASS, FAIL, BLOCKED, NOT RUN or NOT AVAILABLE accurately. A tool/infrastructure absence is not PASS.
Broaden testing only for changes or unresolved risk, not repeatedly after an unchanged successful gate.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. NEVER bypass tests or reset a database to obtain a passing result.

## References

- [Project discovery](references/project-discovery.md)

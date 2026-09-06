# Workspace verification discovery

Resolve package.json upward from each changed file to pnpm-workspace.yaml and the root package.json. Use actual package names and scripts, including check-types, lint and test:run.
Deduplicate workspaces, preserve dependent consumers of changed exports and obey the Turbo graph.

The root verify script runs Turbo checks plus Knip. SQL uses test:postgres; browser uses test:e2e; containers use test:deploy. Missing required executables or fixtures are
BLOCKED/NOT RUN, never silently PASS. Avoid running a root-only command from a package.

## Starter evidence

Read `package.json` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

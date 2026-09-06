# pnpm and Turbo tasks

The root scripts call Turbo tasks, while workspace scripts execute installed tools. Inspect dependencies/outputs before adding a task.
Application entrypoints and deployment configuration define process lifetimes and restart policy.

Use pnpm --filter with package names from manifests. Do not download a missing CLI during a verification gate or invent scripts. Test command exit propagation and actual build artifacts.

## Starter evidence

Read `turbo.json` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

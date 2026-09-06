# Services and composition

AppContext assembles repositories, a per-app SessionEventBus and limits. SessionService receives it once and accepts domain values in public methods. This permits independent
in-memory apps in tests. Keep repositories and services: they are intended boundaries, not redundant wrappers.

When splitting a module, identify its invariant and consumers first. Share contracts through packages; do not import API modules from the worker. Verify isolation with two contexts
and ensure closing one app does not stop another.

## Starter evidence

Read `apps/api/src/core/context.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

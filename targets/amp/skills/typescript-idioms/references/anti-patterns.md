# TypeScript boundary mistakes

Avoid duplicated DTOs, global app state, HTTP-aware domain methods, direct SQL from UI, DOM components in native screens and worker imports from the API. These hide actual boundaries.

Follow emitted ESM .js imports in packages/types and source exports in packages/ui. Do not force one import convention onto the whole monorepo. Verify real consumers and builds.

## Starter evidence

Read `packages/types/package.json` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

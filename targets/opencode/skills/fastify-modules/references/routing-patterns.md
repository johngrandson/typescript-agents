# Module routing

ModuleRegistry registers manifests by unique id, prefix and plugin. registerModules mounts the factories in explicit order. New routes belong in a module and its manifest; inspect
existing route paths and duplicate handling.

Preserve TypeBox params/body/response schemas, async errors and status codes. Fastify injection tests should exercise the mounted path, not only the handler function. /modules
exposes public metadata rather than internal plugin objects.

## Starter evidence

Read `apps/api/src/plugins/registry.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

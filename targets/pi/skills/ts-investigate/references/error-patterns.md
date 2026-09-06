# Error patterns

| Symptom | First evidence |
| --- | --- |
| TypeScript cannot resolve an import | Workspace exports, emitted build, path alias and .js ESM convention |
| Fastify validation failure | Actual TypeBox schema, params/body and canonical error envelope |
| Missing session | Repository null → AppError NOT_FOUND; confirm intended ID/environment |
| Silent web mutation | Server Action result, API response and pending/error UI |
| Stale mobile detail | Request ownership, navigation and REST/WS interleaving |
| Database failure | Safe SQLSTATE, migration history and disposable reproduction |
| Duplicate archive | Job identity, immutable publication and at-least-once retry |
| Worker shutdown hangs | Active RPC/handler, AbortSignal, lease and pool-close order |

Read the literal error before hypothesizing. Unknown errors must remain visible internally; do not classify them as expected absence or validation merely to make a test pass.

## Runtime boundaries

Use a generic read-only subagent only when the host supports it and independent
tracks justify it; otherwise inspect each pattern in this session.
Only when the user explicitly authorizes a fix or temporary diagnostics may
investigation change application source. Preserve unknown errors internally;
never hide them as validation failures merely to make a test pass.

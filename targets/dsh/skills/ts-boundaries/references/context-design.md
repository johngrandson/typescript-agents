# Service and package boundaries

SessionService owns invariants and takes domain values; AppContext injects the repository port, bus and limits. The port exposes storage needs and both adapters implement complete
DTOs. Thin Fastify routes validate/delegate/wrap.

A new module deserves a boundary when it owns a distinct invariant/lifecycle and can expose a useful contract. A shared package is justified by actual consumers; worker/API sharing
requires extraction rather than app-to-app imports. Keep packages/types pure and platform-neutral.

Map callers, effects and tests before changing public methods. Shared DTO exports, server-only modules and DOM/native UI have different consumers. Do not reject services or
repository interfaces merely because another framework organized domain code differently.

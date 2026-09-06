# Mocks at explicit ports

Inject filesystem/document-store or other external effects where the production API already exposes a port. Prefer real memory repositories for domain behavior and a fake socket for transport control.

Assert effects and errors, not just calls that mirror implementation. Exercise duplicate delivery, malformed input and unexpected I/O failure. Restore patched state in teardown and
avoid global singleton contamination.

Starter evidence: `apps/worker/src/handlers/__tests__/archive-session.test.ts`.

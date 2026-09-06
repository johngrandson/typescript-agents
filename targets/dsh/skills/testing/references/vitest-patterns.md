# Vitest isolation

Build a fresh AppContext with memory repositories, limits and a private event bus. Exercise SessionService directly for domain rules; test expected AppError and an unexpected failure separately.

Close owned timers/sockets/pools in teardown. Await assertions and restore mocks/fake timers. Avoid sleep-based synchronization and do not replace failing tests with skipped ones.

Starter evidence: `apps/api/src/modules/sessions/__tests__/service.test.ts`.

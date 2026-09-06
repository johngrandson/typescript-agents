# Async composition

Use await to preserve ownership and sequential effects. Promise.all is suitable only for independent operations. The worker claims one job at a time and awaits the active operation through shutdown.

A timeout race does not cancel real I/O. Pass AbortSignal where supported and keep awaiting owned operations before closing the pool. Test the late-resolution path, not only the timeout callback.

## Starter evidence

Read `apps/worker/src/runner.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

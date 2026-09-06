# Specific catches and cleanup

alreadyPublished handles only DocumentStoreError not-found as false, invalid-document as a permanent failure, and rethrows everything else. Cancellation is checked before handling the caught error.

Use this pattern when absence is expected. Keep try blocks narrow and cleanup in finally; do not replace programming errors with null or success. Tests should inject both the
expected class and an unrelated Error.

## Starter evidence

Read `apps/worker/src/handlers/archive-session.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed
source hashes before adapting them.

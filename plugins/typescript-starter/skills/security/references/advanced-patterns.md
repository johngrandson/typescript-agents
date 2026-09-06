# Storage and failure exposure

JSON storage must constrain directory, filename and validated document shape. Use the existing store/error abstraction; catch only expected not-found or conflict cases and preserve
unexpected I/O failures.

Review traversal, symbolic-link/file boundaries, publication conflicts and malformed persisted data against current tests. databaseErrorMessage strips bound SQL details;
toErrorResponse sanitizes deployed unknown failures. Verify logs as well as HTTP bodies.

## Starter evidence

Read `packages/db/src/document-store.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

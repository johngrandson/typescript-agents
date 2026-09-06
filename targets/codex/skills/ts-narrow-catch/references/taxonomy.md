# Error taxonomy

Expected AppError codes represent domain/HTTP outcomes. Recognized Fastify parser errors become canonical client failures. Unexpected errors remain INTERNAL with deployment-dependent message exposure.

DocumentStoreError uses a kind discriminant; PermanentJobError marks terminal worker failure. DrizzleQueryError needs safe SQLSTATE extraction. Do not classify arbitrary Error
messages as validation, missing data or safe-to-retry events.

## Starter evidence

Read `apps/api/src/core/errors.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

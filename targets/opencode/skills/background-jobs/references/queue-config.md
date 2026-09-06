# Queue configuration

JobRunner processes sequentially; batchSize limits jobs per tick. The lease must exceed handler, shutdown and RPC deadlines, with bounded positive values. Polling must not start
overlapping drain batches.

Read packages/env for defaults and validation rather than inventing concurrency queues. Verify startup misconfiguration, idle ticks and stop during an active claim. Store recurrent
scheduling identity in the database.

## Starter evidence

Read `apps/worker/src/runner.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

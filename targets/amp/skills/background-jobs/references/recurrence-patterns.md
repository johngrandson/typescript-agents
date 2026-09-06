# Recurrence and advanced queue limits

The custom queue persists recurrence keys and run history. registerRecurring rejects changed configuration and does not revive terminal history after restart. Inspect transition
helpers before migrating legacy recurring jobs.

There is no installed workflow-DAG, batch or commercial queue framework. For multi-step effects, define explicit durable states and idempotency only when required. Do not equate
batchSize with parallel processing or recurrence with exactly-once delivery.

## Starter evidence

Read `packages/db/src/__tests__/job-recurrence.contract.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm
changed source hashes before adapting them.

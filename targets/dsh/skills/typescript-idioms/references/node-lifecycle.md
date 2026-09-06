# Node process lifecycle

Node uses explicit start/stop handles and cooperative cancellation. Construct app contexts with separate owned mutable state. Requests in one process share its heap; dispose
timers/listeners and await owned async work.

Inspect process restart policy in the deployment configuration. Blocking work blocks the event loop. Test repeated stop, active requests and resource-close ordering; inspect
the sequential worker and its fenced leases separately.

## Starter evidence

Read `apps/api/src/core/lifecycle.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

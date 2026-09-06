# Loading and stream lifetimes

Read the screen loading hook and its ownership tests. A late REST response must not overwrite a newer selected session; cancellation and request generation serve different
purposes. Web initial reads follow Server Component conventions.

Inspect active subscriptions, recovery snapshots and cleanup on unmount/session change. Verify stale loads, pending mutation transitions and reconnect interleavings; do not ban all
mobile useEffect loading because the web uses server data fetching.

## Starter evidence

Read `apps/mobile/src/screens/SessionDetail/useSessionDetail.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm
changed source hashes before adapting them.

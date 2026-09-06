# Connection participants

Participants are derived from active stream connections, not stored identities. The per-app event bus feeds structural SSE/WS sockets and SessionService merges participants into
snapshots. A random clientId is not an authenticated actor.

Check unsubscribe, closed session, duplicate connections and slow-subscriber handling. Multiple API instances do not share this memory; do not promise distributed presence or
worker publication without a new design.

## Starter evidence

Read `apps/api/src/core/eventBus.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

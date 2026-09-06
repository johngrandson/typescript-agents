# Navigation and shared projection

applySessionEvent is pure shared code for both clients. It ignores other-session events, handles idempotent item additions, reorders/reindexes items and deduplicates participants.
Keep revision/recovery logic compatible with both transports.

Web navigation uses Next conventions; mobile uses React Navigation. On navigation, dispose the old stream and gate old results. Test delete/closed-session behavior and a reconnect
while a screen changes.

## Starter evidence

Read `packages/types/src/session-projection.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source
hashes before adapting them.

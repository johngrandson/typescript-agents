# Platform integration

Native services own WS integration; web uses browser SSE through its server proxy. Keep platform APIs behind their workspace service or hook and validate event payloads before projection.

Handle unavailable network, reconnect, malformed messages and disposal. Do not share DOM code with React Native or browser globals with server-only modules. Test the adapter
contract and report device behavior separately from mocked host tests.

## Starter evidence

Read `apps/mobile/src/services/websocketService.ts` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed
source hashes before adapting them.

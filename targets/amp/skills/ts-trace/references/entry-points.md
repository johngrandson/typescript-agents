# Entry-point categories

| Category | Starter source |
| --- | --- |
| HTTP routes | apps/api/src/modules/sessions/routes.ts |
| SSE/WS admission | The same route factory plus core sseSocket/webSocket |
| Web mutations | apps/web/app/actions/actions.ts |
| Web realtime | session-panel/hooks/use-session-events.ts and the BFF proxy |
| Mobile interactions | screens/SessionDetail hooks and services/apiService.ts |
| Mobile realtime | services/websocketService.ts and stores |
| Worker | registry.ts, runner.ts and handlers/archive-session.ts |

Stop a caller trace at the external request/event/tick, not at an arbitrary utility. Track callbacks from registration to invocation. Shared projection is called by both clients;
the worker does not call the API event bus. Mark any unresolved dynamic edge.

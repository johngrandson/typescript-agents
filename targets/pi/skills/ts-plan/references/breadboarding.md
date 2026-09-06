# React web/mobile breadboarding

Use for two or more pages/screens/components with shared state, multi-step interactions or realtime navigation. Skip for a trivial isolated edit. Preserve the Shape Up mapping
vocabulary: Places P, UI affordances U, code affordances N and data stores S.

## Tables

| ID | Place | Platform | Entry point | Notes |
| --- | --- | --- | --- | --- |
| P1 | Session detail | web | Next route | Server initial snapshot and client events |
| P2 | Session detail | mobile | React Navigation screen | REST load and WS subscription |

| ID | Place | Affordance | Wires out | Returns to |
| --- | --- | --- | --- | --- |
| U1 | P1 | Update name | N1 Server Action | S1 current snapshot/action result |
| U2 | P2 | Update name | N2 ApiService | S2 screen/store snapshot |

Map N nodes to actual functions such as web updateSession, mobile ApiService.updateSession, SessionService.update, repository update and applySessionEvent. S nodes identify owned
state and persistence, not just variable names. Record request ownership, error transitions and cleanup on each asynchronous edge.

## Unknowns and plans

Mark unresolved edges as spikes with a 30-minute time box and observable success criteria. Turn every required wire into a plan task/test or explicit defer. Web uses Server
Actions/SSE and DOM UI; mobile uses REST/WS/native UI. Share contracts/projection, not rendering assumptions. No authenticated actor or distributed bus exists by default.

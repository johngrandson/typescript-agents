# Architecture checks

Inspect manifests, package exports, import edges, shared contracts and test counterparts. Use rg for import candidates and confirm in source. Knip is an unused-code/dependency
signal, not a complete call graph.

| Boundary | Healthy pattern | Defect evidence |
| --- | --- | --- |
| Contracts | TypeBox schemas and Static DTOs in packages/types | Duplicated validator or divergent event projection |
| API | AppContext → SessionService → repository port | Domain logic tied to request/reply or global SQL |
| Persistence | Postgres/memory parity | Different snapshot/null/order/revision behavior |
| Web | Server Actions/server-only client/SSE proxy | Direct component mutation fetch bypassing action policy |
| Mobile | REST/WS services and native components | Next server import or DOM component in native screen |
| Worker | Shared packages, explicit registry and leases | API import, stale ownership acknowledgement |

Score only inspected evidence. Services and repositories are intended design. Confirm dynamic/registry edges before flagging cycles; report unresolved graph coverage. No
authenticated identity or distributed bus is implied by the baseline.

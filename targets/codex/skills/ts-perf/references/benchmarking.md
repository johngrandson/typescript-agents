# Benchmarking and profiles

Define workload, data cardinality, build mode, runtime version, machine and measurement window before collecting a baseline. Record throughput, latency distribution, errors and
memory where relevant. Warmup and cache state must be comparable across runs.

For SQL measure actual query count, rows and plans; a loop alone is not N+1 evidence. For API/runtime record event-loop delay and owned resources. For UI measure renders, retained
state and subscriptions on the appropriate platform. For jobs record claim/handler/acknowledgement time, retry rate and backlog; sequential batchSize limits work per tick.

Change one suspected cause, rerun the same workload and retain both logs. Use confidence intervals/repeated samples when noisy; do not claim a percentage from one request. EXPLAIN
ANALYZE executes queries and requires a disposable target for writes. Browser profiles do not establish native device performance.

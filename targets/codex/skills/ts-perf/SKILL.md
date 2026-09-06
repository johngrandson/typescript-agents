---
name: ts-perf
description: Use when measuring starter SQL/API latency, event-loop stalls, retained
  React state, mobile…
---

# Performance analysis

## Usage

`$typescript-starter:ts-perf [path] [--focus drizzle|react|runtime|jobs]`. Without a focus, inspect the layers involved in the reported symptom. Read manifests, actual workload and environment; do
not assume the database is always the cause.

## Iron Laws

1. Measure baseline and comparison under the same workload and build configuration.
2. NEVER invent query counts, memory estimates or percentage improvements from static code.
3. Change one suspected cause at a time and preserve every selected track’s evidence.

## Parallel tracks

- Drizzle: query-optimizer inspects emitted SQL, counts at multiple cardinalities, projections, indexes and plans. Preserve repository parity and data semantics.
- React: react-architect inspects web and mobile state ownership, render frequency, list bounds, stale loads and subscription cleanup. Device rendering is separate from browser evidence.
- Runtime: node-runtime-advisor inspects event-loop blocking, retained listeners/timers, async concurrency and cleanup. The per-app bus is not distributed.
- Jobs: background-jobs-specialist inspects claim latency, handler duration, retry rate and backlog. batchSize is sequential executions per tick, not concurrency.

Spawn only relevant tracks, wait for all selected reports and retain missing coverage. Prioritize by impact/effort: DO FIRST (high/low), PLAN (high/high), QUICK WIN (low/low), SKIP (low/high).

## Output

Present the top five with path/line, baseline, workload, measurement method, suspected mechanism, proposed change and comparison evidence. Label estimates and unmeasured
hypotheses. Offer `$typescript-starter:ts-plan`, `$typescript-starter:ts-quick` or `$typescript-starter:ts-investigate` according to scope; analysis itself does not edit source. SQL EXPLAIN ANALYZE
executes its query, so mutating probes
require disposable Postgres.

## References

- [Benchmarking](references/benchmarking.md)

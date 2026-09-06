# Documenting the starter

Start with tested changed symbols. packages/types documents TypeBox-derived DTOs and pure projections. packages/db documents port invariants and differences between missing data
and failure. API services document decisions and post-write effects; routes document HTTP schema/envelopes.

Web actions describe server-only mutation behavior and action results. Mobile services describe REST/WS and request cancellation; native support must not be inferred from browser
tests. Worker documentation names sequential batching, fenced ownership, permanent errors, retries and recurrence history.

Verify examples against source and tests before writing. Add README sections for user-facing behavior and ADRs for consequential boundary changes. Avoid undocumented new
authentication, distributed event or queue-framework assumptions.

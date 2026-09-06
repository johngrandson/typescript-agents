# Fixtures and contracts

Use minimal valid Session fixtures and the shared repository contract suite. Factories create data; they must not silently share repositories or mutable arrays between tests.

Run equivalent behavior in memory and Postgres. Preserve snapshot completeness, revision/timestamp semantics and ordering. Type assertions on fixture data do not establish schema validity.

Starter evidence: `packages/db/src/__tests__/session-repository.contract.ts`.

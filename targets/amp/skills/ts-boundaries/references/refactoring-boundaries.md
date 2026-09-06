# Refactoring boundaries

1. Capture incoming/outgoing imports, exported symbols and observable behavior of the affected module.
2. Identify a concrete leak: SQL in routes, an HTTP-aware service, duplicated TypeBox schemas, worker-to-API imports or duplicated client projection.
3. Move one responsibility behind an existing port/service/package boundary. Preserve external method signatures until callers migrate.
4. Update Postgres and memory together when a port changes. Web and mobile adapt transport independently while consuming the same shared contracts.
5. Run typechecks/builds for affected consumers and relevant behavior tests; remove obsolete exports only after every caller is migrated.

Do not do a repository-wide rewrite to fix one boundary. Keep a recoverable diff/commit, never reset or discard unrelated work. Report any dynamic import whose caller remains unconfirmed.

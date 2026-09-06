# Managed review guidelines

When installation is authorized, upsert only the region between TYPESCRIPT-STARTER-REVIEW-GUIDELINES:START and END in project AGENTS.md. Preserve outside content. Do not overwrite
an existing unmanaged Review guidelines section; prepare the proposed merge and identify any unresolved conflict.

```markdown
<!-- TYPESCRIPT-STARTER-REVIEW-GUIDELINES:START -->
## Review guidelines

Review changed code against source, tests and the requested behavior. Cite file/line and a concrete failure path. Distinguish pre-existing issues and missing verification. Avoid speculative style findings.

Prioritize incorrect shared schemas/envelopes, lost revision metadata, unsafe SQL/logging, stale ownership or retry bugs, worker-to-API imports, swallowed unknown errors, and request/subscription cleanup defects. Services/repository ports are intended; web Server Actions and mobile REST/loading hooks have different conventions. clientId is not authentication; the event bus is per API instance and job batchSize is sequential work per tick.

Confirm package exports and built ESM imports, Postgres/memory parity and platform-specific tests. Do not claim browser checks verify native rendering or a missing integration passed. Never fix application code from a read-only review role.
<!-- TYPESCRIPT-STARTER-REVIEW-GUIDELINES:END -->
```

Record the actual installed CLI/runtime behavior independently from the instruction block. This setup does not publish a PR comment or install global safeguards.

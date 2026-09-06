---
name: ts-document
description: Use when documenting tested TypeScript APIs, TypeBox contracts, Fastify/OpenAPI
  behavior, README sections or ADRs; not for docs lookup.
---

# Document

Generate documentation for newly implemented features.

## Usage

```
/ts-document .claude/plans/magic-link-auth/plan.md
/ts-document magic link authentication
/ts-document  # Auto-detect from recent plan
```

## Iron Laws

1. **Never remove existing documentation** — Existing docs may reflect design intent that isn't obvious from code alone; update rather than replace
2. **module JSDoc on every public module** — Undocumented modules accumulate quickly and create onboarding friction for new team members
3. **ADRs capture the "why", not the "what"** — Code shows what was built; ADRs explain why this approach was chosen over alternatives
4. **Match API JSDoc to function's public API** — Document parameters, return values, and edge cases; callers shouldn't need to read the implementation
5. **DO NOT add API JSDoc to untested code** — documentation implies a stable contract; document only after tests confirm the function behaves as described

## What Gets Documented

| Output | Description |
|--------|-------------|
| `module JSDoc` | For new modules missing documentation |
| `API JSDoc` | For public functions without docs |
| README section | For user-facing features |
| ADR | For significant architectural decisions |

## Workflow

### Step 0: Pre-check (avoid no-op runs)

Inspect changed TypeScript/TSX exports, runtime contracts and implemented plan tasks. Include behavior/signature changes in existing files, not only newly added modules. If no
public behavior or documentation changed, report the no-op with evidence instead of generating boilerplate.

1. **Identify** changed public APIs/modules from recent commits or plan file
2. **Check** TypeBox schemas and the registered OpenAPI surface against tested request/response behavior. Update API documentation when schema or envelope changes; do not claim
   generated docs verify runtime behavior. Then check documentation coverage (`module JSDoc`, `API JSDoc`)
3. **Generate** missing docs using templates
4. **Add** README section if user-facing feature
5. **Create** ADR if architectural decision was made
6. **Write** report to `.claude/plans/{slug}/reviews/{feature}-docs.md`

## When to Generate ADRs

| Trigger | Create ADR |
|---------|-----------|
| New external dependency | Yes |
| New database table | Maybe (if schema non-obvious) |
| New Node runtime process | Yes (explain why process needed) |
| New context | Maybe (if boundaries non-obvious) |
| New auth mechanism | Yes |
| Performance optimization | Yes |

## Integration with Workflow

```text
/ts-plan → /ts-work → /ts-review
       ↓
/ts-document  ← YOU ARE HERE (optional, suggested after review passes)
```

## References

- `references/doc-templates.md` — module JSDoc, API JSDoc, README, ADR templates
- `references/output-format.md` — Documentation report format
- `references/doc-best-practices.md` — TypeScript documentation best practices
- `references/documentation-patterns.md` — Detailed documentation patterns

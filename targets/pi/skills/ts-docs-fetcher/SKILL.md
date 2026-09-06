---
name: ts-docs-fetcher
description: Fetch official docs, TypeScript declarations and changelogs for exact
  npm versions resolved by pnpm. Use for package API research, including Fastify registration,
  React hooks and Drizzle queries, or upgrade compatibility.
---

# Version-aware documentation

Use `/skill:ts-docs-fetcher` for package APIs, exact-version changelogs and dependency research. Resolve
the package's declared name or alias in one importer; different consumers may have different
versions.

## Usage

```bash
python3 "scripts/docs_fetcher.py" react --root "$PWD" --importer apps/web --query useActionState
python3 "scripts/docs_fetcher.py" fastify --root "$PWD" --importer apps/api --query register --offline
```

## Documentation rules

Read the exact locked package's available verified tarball first. Its README, changelog,
declarations and source provide version-specific evidence. The executable validates archive identity
and extracts only safe members. It searches locally and returns bounded excerpts; it never imports
package code, invokes lifecycle scripts or installs a package.

When local/package evidence is insufficient, use an explicit official versioned documentation URL.
Pass `--url` and `--url-version` only when the page actually states that version. Never manufacture
`/version/` URLs. An unversioned official page is allowed with an express applicability limitation,
not labeled as documentation for the installed version.

The program writes package/version/importer/timestamp/URL/content digest and focused excerpts
beneath `.claude/plans/<slug>/research/docs/`. A persistent URL+locked-version cache verifies
content digests and expires mutable pages after 24 hours. Offline returns available content with
freshness stated; missing content remains incomplete. A stale page may still be useful evidence but
must be described as stale.

Use one API-focused query instead of mirroring an entire website. Preserve source attribution in the
final research answer, compare peer and runtime requirements, and surface differences between
documentation and installed types. The workflow may consult web sources through available tools, but
fetching docs is never permission to mutate the application.

## Iron Laws

1. Resolve one declared package name or alias in the selected importer and record its exact locked version before interpreting an API.
2. NEVER import package code, execute lifecycle scripts or install dependencies to fetch documentation; use verified bytes and bounded excerpts.
3. Verify an explicit official URL and its stated version. Label unversioned, mismatched or stale evidence with its applicability limit; never invent a versioned path.
4. Preserve URL, version, digest, timestamp and evidence path in the result. Report missing content as incomplete and conflicting installed types as unresolved evidence.

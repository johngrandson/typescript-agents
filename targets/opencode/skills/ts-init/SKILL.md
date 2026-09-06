---
name: ts-init
description: Use when installing/updating TypeScript starter project rules, Fastify/Drizzle/React
  skill routing, verification guidance or managed review guidelines.
---

# Plugin initialization

## Usage

`/ts-init [--update]` installs project-local guidance; it does not install globally or overwrite unrelated rules.

## Workflow

1. Read CLAUDE.md, AGENTS.md and existing markers. Detect pnpm workspaces and package names from manifests/lockfile, then verify Fastify/TypeBox, Drizzle, Next, Expo and worker
   paths. Do not infer the current stack from stale framework prose.
2. Fresh install: append the relevant guidance from `references/injectable-template.md` between `<!-- TYPESCRIPT-STARTER-PLUGIN:START -->` and `<!-- TYPESCRIPT-STARTER-PLUGIN:END -->`.
3. Update: replace only that managed region. Preserve all bytes outside it. If markers are corrupt, prepare a recoverable patch and report the ambiguity rather than deleting unrelated content.
4. Fill date, plugin version 1.0.0 and detected versions; include only capabilities confirmed in the checkout. Shared contracts, services/repositories, web/mobile separation,
   custom jobs and verification have explicit routing.
5. If Codex review guidance is requested or already authorized, manage the separate AGENTS.md block in `references/codex-review-guidelines.md`. Preserve existing unmanaged review
   guidelines and avoid duplicate sections. An installed CLI alone is not permission to overwrite them.
6. Validate marker uniqueness, references and detected facts. Show the changed region and installed capabilities. Unknown/missing manifests are a discovery error, not a reason to enable all features.

## Runtime boundary

Use the distribution's documented init behavior for the active runtime. A managed instruction block is guidance, not proof that hooks or native safeguards are installed. Old plugin
installations may coexist; do not mutate personal registrations or remove their markers automatically.

Report the local files changed, detected stack, loaded sections and verification. Read existing session authorization before requesting another decision.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. NEVER bypass tests or reset a database to obtain a passing result.

## References

- [Codex review guidelines](references/codex-review-guidelines.md)
- [Injectable template](references/injectable-template.md)

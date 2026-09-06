---
name: ts-deploy
description: Use when editing Docker/Compose, production builds, environment validation,
  migrations, health…
---

# Deploying the starter

Read the current `Dockerfile`, Compose files, entrypoints, `packages/env`, `packages/db/src/migrate.ts` and `apps/e2e/support` before preparing deployment changes. This skill
prepares and validates artifacts; publication or a live deploy needs authorization.

## Usage

```text
pnpm verify
pnpm build
pnpm test:deploy
```

## Contract

- Node runs API and worker builds. pnpm installs from the lockfile and Turbo orders package builds. Existing Docker targets include `api`, `web`, `worker` and `development`; the
  mobile workspace is excluded from production images.
- `packages/types`, `db`, `env` and `logger` publish compiled artifacts. Web runs its Next standalone output. Match actual package exports and image COPY paths.
- Validate env through `packages/env`; never copy secrets into build layers or public Next/Expo variables. The runtime uses a non-root user and a writable data directory.
- Run reviewed migrations before API/worker consumers. Inspect `pnpm db:deploy`, entrypoint behavior and Compose dependencies. Do not substitute `db:push` or a destructive reset for migration review.
- Confirm health routes, exposed ports, persistent volume ownership and the graceful shutdown order. Worker shutdown must drain/stop work before closing storage; API shutdown must
  clean streams, timers and pools.
- Do not imply that a platform-specific deployment file exists. Adapt the existing Docker/Compose contracts to a requested host only after checking its actual requirements.

## Verification

Run `pnpm verify`, relevant builds and `pnpm test:deploy` with the required disposable environment. Verify a clean migration and previous-schema upgrade; test health, a Session
write/read and worker execution against persistent storage. Record browser smoke separately from mobile exports/device behavior. A successful image build alone is not a deployed
service.

Report image targets, env contract, migration order, health/smoke evidence, rollback constraints and unexecuted checks. Never push an image or change a live database merely to produce a green report.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

## References

- [Docker config](references/docker-config.md)
- [Host adaptation](references/host-adaptation.md)

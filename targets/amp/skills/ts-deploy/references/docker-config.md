# Docker targets and runtime

The build uses Node, pnpm frozen installs, Turbo, deployable API/worker trees and Next standalone output. Mobile dependencies are excluded from server images. Runtime runs as node with writable /data.

Check manifest COPY paths, package exports, env separation, migration entrypoint and non-root volume permissions. Run deploy smoke for persistent writes and health. A cached
successful build is not proof of migration ordering.

## Starter evidence

Read `Dockerfile` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

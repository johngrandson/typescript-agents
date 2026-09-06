# Version and workspace compatibility

Read exact resolved TypeScript, Node, React, Next and Expo versions. Workspace compatibility differs: web React and mobile React may resolve different supported versions. Do not
homogenize them from memory.

Use package scripts and official installed-version documentation when changing language/runtime features. Validate both compiler and runtime targets, Expo compatibility and built ESM imports.

## Starter evidence

Read `pnpm-lock.yaml` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.

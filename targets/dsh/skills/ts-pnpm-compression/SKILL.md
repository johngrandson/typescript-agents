---
name: ts-pnpm-compression
description: Use when verbose pnpm, Turbo, TypeScript, ESLint or Vitest output obscures
  errors; retain raw logs and original command exit status.
---

# pnpm output compression

## Usage

```text
rtk --version
rtk verify
```

## Workflow

1. Detect `rtk` and inspect its installed version/help. Compression is optional; verification tools remain required. Do not install a global binary or hook without authorization.
2. Merge the bundled conservative filters into project `.rtk/filters.toml`, preserving user sections. Names are pnpm-test, pnpm-types, pnpm-lint and turbo-checks. Match installed
   RTK support before enabling them.
3. Run `rtk verify` for embedded fixtures. Also compare a real failing command with raw output: diagnostics, filenames, stack traces and exit status must survive. Never infer
   success from a summary line or empty output.
4. Use the configured command routing only if observed. If RTK cannot filter pnpm, run the real command and summarize its saved output; do not claim a shell rewrite was installed.

## Safety of summaries

Preserve full logs outside the conversation and the command exit code before summarizing. Avoid `command | tail` without pipefail because it can hide a failing process. Do not
short-circuit a log on an early passing test when a later test fails. Blank lines and identified progress banners may be removed; failure/warning blocks must remain.

No performance or token-saving percentage is promised. Report the raw command, status and log path, plus whether optional compression was available.

## Iron Laws

- Verify the actual workspace and cited source before applying the recipe.
- Preserve the domain, platform and runtime limits stated above; a missing capability is not an installed framework.
- Keep failures and unexecuted checks visible. Never bypass tests or reset a database to obtain a passing result.

## References

- [Install](references/install.md)
- [Rtk filters](references/rtk-filters.toml)

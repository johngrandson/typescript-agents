# Security

This harness contains executable hooks and dependency tools. Claude runs the
canonical hooks; other runtimes install only the capabilities documented in
[the runtime matrix](docs/runtime-support.md). Skill text does not create a
security boundary or install an application authentication system.

## Local safeguards

The destructive-command hook checks actual shell command tokens and declared
workspace scripts. The freeze hook constrains scoped edits. Checks preserve
failure output, avoid running application mutations and record their limits in
[HOOKS.md](HOOKS.md). Their tests use isolated fixtures, never development data.

The dependency auditor verifies locked artifacts, integrity and extraction
boundaries; scans TypeScript/JavaScript; distinguishes advisory, heuristic and
incomplete evidence; and separates auditing from explicit vetting. Synthetic
fixtures and captured metadata cannot produce a security approval. The gate
checks whether evidence still matches the current dependency state.

Review the executable source and test evidence under
`plugins/typescript-starter/skills/deps-audit` and
`docs/quality/verification.md`.
Missing tools, unavailable advisories or stale evidence must remain visible;
they cannot be reported as a clean audit.

## Optional independent scans

`make security` runs the installed SkillSpector scanner when available.
`lab/skillspector/scan.sh` uses its static mode. A missing scanner is reported as
not run. Earlier scanner scores and suppressions do not establish the current
checkout's safety. Review any baseline against the changed file and exact
finding before accepting it.

Normal tests and structural evaluations are local. Fresh provider evaluations,
registry capture and externally published releases are separate operations.
Registry capture is disabled unless explicitly enabled for this repository,
and captured responses never write the approved dependency ledger.

## Reporting

Provide the affected revision, component, reproducible behavior and a minimal
sanitized example to the maintainer of the installed checkout. Avoid including
tokens, credentials, private package metadata or real user data.

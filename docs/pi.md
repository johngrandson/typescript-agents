# Pi installation

`targets/pi` is the standalone `pi-typescript-starter` package. The root
package also exposes `targets/pi/skills` through its `pi.skills` declaration.
Both contain the same 51 generated skills.

## Install locally

```bash
pi install /absolute/path/to/typescript_starter_harness/targets/pi
```

For a project-scoped installation, use the installed Pi CLI's local-install
option. Start a new Pi process in the application and invoke:

```text
/skill:ts-plan Add a session operation
/skill:ts-investigate Failing worker lease test
/skill:drizzle-constraint-debug packages/db
```

## Contract

Only skills and their resources are installed. The target does not install
extensions, prompt templates, hooks, custom agents, root instructions or MCP
configuration. Native subagent features are optional and have sequential
fallbacks. Freeze is advisory and does not create `.claude/.freeze`.

Use Node 22.19 or later. Dependency audit tooling has its own explicitly pinned
setup instructions in the audit skill; a missing parser produces an incomplete
audit, never a security approval.

Refresh the local package after regenerating the target and restart Pi. Remove
only this harness's package entry when uninstalling. Installation, update,
clean reinstall, ref change and uninstall take effect in a fresh process.

```bash
make pi-skills-validate
make pi-runtime-smoke
```

The optional smoke runner uses isolated settings and RPC discovery, checks
resources and verifies lifecycle behavior. It does not perform a paid model
trigger evaluation. See the [runtime matrix](runtime-support.md).

# DeepSeek Harness installation

Copy the **contents** of `targets/dsh/skills` into a scanned skill root. dsh
scans one directory level: `<skill-name>/SKILL.md`. A nested checkout containing
`targets/dsh/skills` is not a discovered skill.

```bash
mkdir -p /path/to/application/.dsh/skills
cp -a /path/to/typescript_starter_harness/targets/dsh/skills/. \
  /path/to/application/.dsh/skills/
```

Check for same-name skills before copying, preserve resource modes, and update
or remove only the 51 directories belonging to this harness. Supported roots
also include project `.agents/skills`, `$DSH_HOME/skills`, `$DSH_AGENTS_HOME/skills`
and configured `customSkillDirs`. Advanced configuration must account for the
active profile's skill-filesystem provider; the default web profile delegates
local discovery to its agent presets.

## Invocation and boundaries

```text
/ts-plan Add a session archive flow
/ts-review
/drizzle-n1-check packages/db
```

The host recognizes a whitespace-bounded public `/name` token before a model
step and injects that skill's body. Native skill tools can load knowledge
skills. Descriptions stay below the host's 500-character discovery limit.

dsh reads `CLAUDE.md` natively. The generated target installs no hooks, MCP
servers, separate command registry or custom-agent registry. dsh subagents use
personas, not a registry of Claude Markdown agents. Workflows have sequential
fallbacks; freeze is advisory and does not create `.claude/.freeze`.

Start a fresh host after install, update, ref changes, clean reinstall or
uninstall. A copied tree does not refresh an active session's catalog.

```bash
make dsh-skills-validate
make dsh-runtime-smoke
```

The optional smoke runner boots an isolated local web host and uses its RPC
boundary. It requires the matching dsh installation; fixture protocol tests do
not establish a live host or provider run. See the
[runtime matrix](runtime-support.md).

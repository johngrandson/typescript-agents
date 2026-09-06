# OpenCode installation

Install the 51 generated skill directories from `targets/opencode/skills` into
a project skill root supported by the installed OpenCode version. Keep the
skill directory names intact and copy complete resources with their modes.

For the project's `.opencode/skills` root:

```bash
mkdir -p /path/to/application/.opencode/skills
cp -a /path/to/typescript_starter_harness/targets/opencode/skills/. \
  /path/to/application/.opencode/skills/
```

Check for existing same-name skills before copying. Update only the directories
owned by this harness, and remove those directories when uninstalling. A fresh
process is required after install, update, ref changes, clean reinstall or
uninstall; an existing session may retain its catalog.

Use the native skill tool to load `ts-plan`, `ts-review`, `ts-investigate` or
`drizzle-n1-check`. Host slash aliases are optional; native skill discovery is
the supported contract.

## Boundaries and verification

This target contains skills only. It does not install hooks, custom agents,
separate commands, root instructions, permissions or MCP servers. Generic
native workers are optional; workflows remain complete sequentially. Freeze
sets an advisory scope and does not write the Claude sentinel.

```bash
make opencode-skills-validate
make opencode-runtime-smoke
```

The optional runner uses isolated config and `opencode debug skill --pure` for
discovery on the supported host interface. It records actual host behavior.
See the [runtime matrix](runtime-support.md) and
[verification record](quality/verification.md).

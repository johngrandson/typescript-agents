---
name: release
description: |
  CONTRIBUTOR TOOL - Prepare and publish a plugin release: choose a version,
  update manifests and CHANGELOG, run the local gate, commit, tag, and publish
  only with approval. Use when shipping a new plugin version. NOT distributed.
argument-hint: "[patch|minor|major] | [X.Y.Z]"
effort: medium
---

# Plugin release

Prepare a versioned release of the TypeScript Starter Harness. This contributor
tool supports a repository with no tags and does not assume a hosted release
already exists.

## Iron Laws

1. **Never release with a failing local gate.** Run `make ci` before the
   release commit and fix failures.
2. **Never use `claude plugin tag`.** This repository uses a marketplace layout.
   Create the Git tag with Git after the release commit.
3. **Keep versions aligned.** The TypeScript starter manifests, CHANGELOG
   heading and `vX.Y.Z` tag must match. `catchup` has its own version.
4. **Confirm before publishing.** Show the exact commit, tag, destination and
   release notes before pushing or creating a hosted release.
5. **Bump plugin metadata for an update.** Installed plugins use manifest
   versions to detect updates.
6. **Keep a fresh `## [Unreleased]` section.** Move its contents into the new
   version section and leave an empty section above it.
7. **Never force-push.**
8. **Use real documentation links.** A local checkout may use repository paths.
   Add hosted links only after a publication destination exists.
9. **Lead with required upgrade steps.** If users must do more than update the
   plugin, put the tested commands at the top of the release notes.

## Step 0: inspect the release state

- Confirm the intended release destination. This checkout does not define one.
- Work from the release branch with a clean tree except for intended files.
- Read `plugins/typescript-starter/.claude-plugin/plugin.json` and the
  `## [Unreleased]` section in `CHANGELOG.md`.
- Find the newest semantic version tag without assuming one exists:

```bash
latest_tag="$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' \
  --sort=-v:refname | head -n 1)"
printf '%s\n' "${latest_tag:-no release tags}"
```

If there is no tag, treat this as a first release. Use an explicitly requested
version. Without one, use the current manifest version when the Unreleased
contents describe that version; ask before choosing a different number.

With an existing release tag, choose the bump from the Unreleased changes:

- **major** for a breaking command or workflow change;
- **minor** for a new skill, agent, command or hook;
- **patch** for a compatible fix or documentation update.

## Step 1: update manifests and generated targets

Set `"version"` to `X.Y.Z` in:

1. `plugins/typescript-starter/.claude-plugin/plugin.json`
2. `plugins/drizzle/.claude-plugin/plugin.json`
3. `plugins/react/.claude-plugin/plugin.json`
4. `package.json`
5. `.claude-plugin/marketplace.json` under `metadata.version`

Leave `plugins/catchup/.claude-plugin/plugin.json` at its independent version
unless the release explicitly changes `catchup`. Update the lockfile only when
dependency metadata changes.

Regenerate the runtime distributions and review the changes before accepting
their digests:

```bash
make amp-skills codex-skills pi-skills opencode-skills dsh-skills
git diff --stat
git diff --summary
make generated-skills-snapshots
make generated-skills-sync
```

Confirm the source and generated versions:

```bash
grep -rn '"version"' plugins/*/.claude-plugin/plugin.json package.json \
  .claude-plugin/marketplace.json targets/codex/.codex-plugin/plugin.json \
  targets/pi/package.json
```

## Step 2: update the changelog

Move the current `## [Unreleased]` entries into
`## [X.Y.Z] - YYYY-MM-DD`. Add a new empty Unreleased section above it. Do not
include changes outside this release. See
`${CLAUDE_SKILL_DIR}/references/templates.md`.

Update `README.md` or the intro tutorial only when commands, counts or install
instructions changed.

## Step 3: run the current local gate

```bash
make ci
```

This runs Markdown lint, Python and shell tests, offline manifest and inventory
validation, generated target checks, snapshot checks, and structural evaluation
for all 51 skills and 26 agents. `make security` is an optional local scan when
SkillSpector is installed. Provider, runtime, database and device checks remain
separate; record only checks that ran.

## Step 4: commit and tag locally

Stage only the release files and use a semantic commit:

```bash
git add CHANGELOG.md .claude-plugin/marketplace.json package.json \
  plugins/typescript-starter/.claude-plugin/plugin.json \
  plugins/drizzle/.claude-plugin/plugin.json \
  plugins/react/.claude-plugin/plugin.json targets/ \
  scripts/generated_target_snapshots.json
git commit -m "chore(release): prepare vX.Y.Z"
git tag vX.Y.Z
```

Add a coauthor trailer only when a contributor asks for one. Confirm that the
tag points to the release commit and that the tree is clean.

## Step 5: confirm and publish

Stop before any push. Show the user:

- the release destination and branch;
- `git show --stat --oneline vX.Y.Z`;
- the pending tag;
- the complete release notes;
- the local checks that passed and any checks not run.

After explicit confirmation, push with the commands appropriate to the chosen
destination. Create a hosted release only when that destination supports one.
Do not claim publication until the remote tag and release can be read back.

## Reference

- `${CLAUDE_SKILL_DIR}/references/templates.md` contains changelog, notes and
  verification templates.

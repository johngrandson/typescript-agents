# Consumer groups and verification

Groups are scoped to an importer, not global name equality. Next/React/ReactDOM and Next lint
integration belong to web. Expo/React Native/React and Expo modules belong to mobile. The starter
deliberately has different web/mobile React versions. Preserve that difference unless the actual
consumer requirements demand a change.

Other groups include Fastify/plugins/TypeBox, Drizzle ORM/Kit/driver, Vitest/coverage, and
ESLint/plugins/shared configuration. Versions across distinct libraries do not need to be equal. A
group's minimum compatibility change may include another package, but document why it is necessary
and stay within the user's authorized scope.

Inspect exact old/new package changelogs and peer contracts before editing. Candidate metadata and
tarballs come from the configured registry and use the audit fetcher. Source URLs and metadata
hashes belong in the update evidence. Major updates require explicit exact requirement edits. Do not
erase workspace protocols, scoped aliases or local patch identities.

Prepare the resolution with lifecycle disabled, then audit the resulting lock. Pre-update approval
only certifies the old graph. Once the new state satisfies audit and vetting, install frozen, run
`pnpm verify` and affected tests/builds. If Expo-specific validation is needed, use an existing
local version-compatible command; do not invent an installed Doctor or fetch one with `dlx`.

The update driver saves before-state and command outcomes under
`.claude/deps-audit/runs/update-<runId>/`. It deliberately leaves a failed prepared state reviewable
instead of rolling back unrelated working-tree changes. Repair the precise incompatibility and rerun
verification; do not commit a failed build. Patch groups can share a verified maintenance commit,
minors should stay by area, and majors by coupled consumer group.

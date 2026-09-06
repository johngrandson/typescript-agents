# Cache, fixtures and gate identity

All runtimes share `.claude/deps-audit/`: `last-run.json`, `runs/`, `cache/` and `evidence/`. Cache
uses restrictive permissions. Atomic tarball publication requires both bytes and a completion
marker. SRI is checked on every reuse; metadata hashes cannot override lock SRI. Rule results are
freshly computed, so no finding cache can substitute for verifying artifact bytes. Tarballs unused
for 30 days may be removed; evidence is never cleaned.

`--offline` disables registry requests. Valid complete cache can satisfy an audit. Missing or
expired metadata/advisories, partial tarball cache and changed bytes result in `incomplete`.
Auxiliary publisher data can be unavailable without inventing evidence.

Fixture mode is opt-in with `--fixtures DIR`. `index.json` declares `kind: synthetic|captured`,
origin, SHA-256 for every referenced file, metadata mapping `registryURL|name@version`, tarballs
mapping exact SRI, and advisory file or OLD/NEW file mapping. Packuments use `name@*`. Fixture reads
verify hashes, disable network, do not populate production tarball cache and can never emit reusable
approval. The hermetic tests generate synthetic archives and advisories. The copied starter
lock/manifests are captured graph input, not scanned package evidence.

Gate reuse lasts at most ten minutes. It checks schema/status/mode, input hashes, scanner/tooling
hashes, valid source TTLs, base commit and cached artifact bytes. Inputs include lock, all importer
manifests, workspace config, effective registry routing, patch contents, policy and ledger. `strict`
and `full` require the entire graph. Missing/malformed ledgers do not turn a mandatory policy into
an advisory pass.

Default policy without a ledger is advisory. A seeded ledger defaults to `new_only` with
`safe_to_deploy`. `warn` records concerns, `new_only` requires newly introduced artifact identities,
`strict` requires every artifact, and `full` also requires configured optional tools. Quick checks
never replace mandatory vetting. Preparation with `--lockfile-only --ignore-scripts
--ignore-pnpmfile` can produce a state for review; install scripts and rebuild require an audit of
that resolved state.

An explicit override records its real authorization and reason in workflow evidence; it does not
rewrite the auditor's result. The CLI does not create approvals to make installation proceed.

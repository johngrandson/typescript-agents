---
name: ts-deps-audit
description: Audit pnpm lock changes and npm package bytes for supply-chain risks,
  lifecycle effects, publisher changes and advisories. Use after dependency changes,
  on lockfile PRs, or to preview candidates without installation.
---

# Dependency audit

Use `ts-deps-audit` to inspect the requested dependency state without changing application
manifests, lockfile, configuration or source. The executable driver owns collection, scanning,
comparison, reports and cache. Never replace a failed source with an empty result or treat a fixture
as package approval.

## Run

```bash
python3 "scripts/deps_audit.py" --root "$PWD" --all --json
python3 "scripts/deps_audit.py" --root "$PWD" --base main --sarif audit.sarif
python3 "scripts/deps_audit.py" --root "$PWD" --preview react --offline
```

Without `--all`, `--base` or `--preview`, compare `HEAD` with the working tree. Missing base is an
error. An empty diff returns `no_changes`, which does not certify the graph. Preview preserves each
importer's requirement and selects stable candidates with npm semver. Explicit `name@version`
supports packages absent from the project. Preview describes candidate peers but does not claim to
have resolved the resulting graph. `--quick` runs metadata/advisory checks only.

Use Python 3.12+, PyYAML, Node 22+, Git and the project's pinned pnpm. The scanner requires directly
declared TypeScript 5.9.3 and semver 7.7.2. The harness already provisions them. Portable
installations can point `TS_AUDIT_TOOLING` to a directory whose manifest explicitly declares these
installed versions; the skill also includes an isolated `scripts/package.json` for deliberate
provisioning. A directly declared matching parser in the application can be resolved with
`createRequire`. Missing tooling produces `incomplete`; the auditor never installs it or searches
accidental transitive dependencies.

## Read the evidence

The pnpm-lock.yaml graph keeps artifact identity separate from importer occurrences, aliases, full
peer snapshots and graph edges. Workspace links remain local. All locked optional/platform artifacts
remain in the inventory. Package archives are SRI-verified before safe extraction; scripts, binaries
and package imports never execute. See [the implementation
contract](references/implementation.md).

Eight native families inspect bidi controls, dynamic evaluation, lifecycle effects, decoded
execution, source changes, historical version publishers, opaque payloads and name similarity. The
TypeScript AST supports common direct aliases and intra-file flows. Arbitrary wrappers and
cross-file flow remain a recorded limitation. `JSON.parse` alone is benign. A lifecycle script alone
is a WARN; a demonstrated dangerous chain can BLOCK.

Advisories come from `pnpm audit --json` in coherent temporary project copies. High/critical
exposure blocks, moderate warns, low informs, and missing severity warns explicitly. Version
deprecation is separate. OLD/NEW exposure comparison preserves multiple vulnerable versions and
importer impact. No package-manager `--fix`, registry-error suppression, `dlx`, package lifecycle or
paid service is used.

Semgrep, YARA and OSV-Scanner are optional local layers. Their absence is recorded; installed-tool
failures are coverage failures. Policy `full` requires each configured optional layer. Local
Semgrep/YARA rules live in `priv/`. Offline never runs OSV network collection.

The driver sets `triageRequired` for any active BLOCK or score >=9 with BLOCK=10, WARN=3 and INFO=1.
Send those findings and metadata to `npm-deps-triager`; `--no-llm` disables this request and `--llm`
forces it. A triager's conclusion is review evidence. It cannot silently alter original severity.
Record justified false-positive decisions through `ts-deps-vet`, identifying the real reviewer.
Accepted risk requires actual authorization already in the session.

## Outputs and gate

`.claude/deps-audit/last-run.json` uses schema 2; each run also writes JSON and Markdown under
`runs/<runId>/`. `--sarif PATH` preserves findings and original severity in SARIF properties.
`--json`, `--quiet` and `--ci` affect presentation only. The initial incomplete sidecar invalidates
old approval before collection.

| Status | Exit | Meaning |
| --- | --- | --- |
| `clean` | 0 | Complete requested scope, no active findings |
| `findings` | 0, or 2 with strict WARN | WARN/INFO remain |
| `blocked` | 2 | Active BLOCK, rejection or unmet vet policy |
| `no_changes` | 0 | No audit of the complete graph was claimed |
| `incomplete` | 3 | Tool/source/input/coverage failure, including interruption |
| `invalid_request` | 64 | Invalid flags or parameters |

BLOCK plus coverage failure remains `incomplete` and retains the BLOCK. `audit_passed` is only true
for a complete real run satisfying policy. Quick, preview, fixture and `no_changes` cannot satisfy a
real gate. `--gate-check --gate-mode strict` validates an existing result in a short hook; it never
performs a network audit. Hooks in supported runtimes call this same CLI. Other runtimes enforce it
in the workflow or CI and must state that they lack hook prevention.

Read [cache, fixtures and gate identity](references/cache-and-gate.md) and [the
review ledger](../ts-deps-vet/references/ledger.md). Preserve original evidence
when comparing or applying a review.

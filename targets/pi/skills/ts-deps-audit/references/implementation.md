# Executable implementation

`deps_audit.py` is the sole auditor CLI. It imports `audit_core.py`, `transport.py`, `analysis.py`
and `ledger.py`; AST and semver parsing use the sibling CJS programs. Python does orchestration and
safe filesystem handling. Package code remains data.

`audit_core.resolve_graph(root)` requires pnpm lock format 9.0. Safe YAML rejects duplicate keys,
YAML aliases and unknown formats. Snapshots preserve balanced nested peer/patch suffixes. Artifact
identity hashes source, real name, version, SRI and patch hash. Occurrences retain importer,
dependency section, declared alias, specifier, complete snapshot and shortest consumer path. The
complete edge list preserves all alternate routes and cycles without exponential path enumeration.
Auto-installed peer dependencies are explicitly marked. Declared overrides must match the lock.
Registry configuration reads scope mappings and hashes effective routing without disclosing tokens.

Normal workspace and link targets must have the declared name and remain in the workspace tree.
Local files have content identities; unsupported or unverifiable external sources produce incomplete
coverage. Patch data is checked for traversal and applied with `git apply --no-index` only inside
the run's extracted artifact. Both original and effective bytes are scanned. A patch never inherits
approval from the original artifact.

Limits default to 100 MiB compressed, 1 GiB expanded, 100000 members and 10 MiB per text file. Flags
can explicitly raise them; values are recorded. Gzip validation checks truncation/CRC. Extraction
validates all entries before writing regular files without executable permissions. Absolute paths,
traversal, duplicate names, devices, escaping links and files beneath links are rejected. Internal
links are inventoried without being materialized. Binary, minified and source-map files remain
visible. Nested package manifests record bundled dependencies.

The registry fetcher permits HTTPS only, rejects redirects and sends a scoped token only to its
configured origin/path. No public fallback exists for private registries. HTTP 401/403/404 stay
distinguishable. It allows at most four concurrent package inspections and one registry/tarball
request every 200 ms. `pnpm audit` manages its own registry protocol in an isolated project copy.
Metadata expires after 24 hours and advisories after one hour.

Native fingerprints are stable across line movement; ledger matching also checks artifact identity
and evidence hash. Differential display marks `new`, `carried` and `dropped` without changing
severity. Exposure comparison joins advisory aliases and preserves every version per importer and
across the graph. The same collected advisory union is applied to both states when available;
unavailable data yields `not_comparable`.

The protected-name list comes from direct external dependency names in the recorded starter
snapshot. It is only a comparison baseline, not trust. Levenshtein <=2 or scope substitution emits
WARN and makes no claim about popularity. Version metadata `_npmUser` supplies historical publisher
evidence; current maintainer lists are not used as a historical substitute. Missing publisher
evidence is `unavailable`.

Parser failure, resource limit, installed optional-tool failure and missing mandatory sources all
prevent approval. The analyzer resolves common imports, destructured require bindings and variable
flows inside a file; arbitrary wrappers, aliases after mutation and cross-file flow remain
limitations. Human interpretation is still needed for plausible findings.

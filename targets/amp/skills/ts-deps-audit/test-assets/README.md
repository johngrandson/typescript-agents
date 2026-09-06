# Dependency audit test inputs

`starter-lock/` is a captured, hash-inventoried lock and importer-manifest snapshot. It proves graph
resolution, overrides, automatically installed peers and distinct web/mobile React versions. It
contains no downloaded npm package bytes, advisory claims or approvals.

`synthetic/native-cases.json` contains small, deliberately synthetic source cases. The behavioral tests
in `scripts/tests/test_dependency_workflows.py` construct tarballs, registry responses and advisory replies
from local data. Each generated fixture has an explicit `synthetic` index and content hashes. The suite
also exercises source/publisher changes, aliases, catalog drift, patches, local dependencies, safe
extraction, the review ledger, cache invalidation, lifecycle non-execution and portable CLI paths.

Run the harness test suite with `.venv/bin/python -m pytest scripts/tests/test_dependency_workflows.py`.
Default tests contact no external services and grant no trust to real packages. Registry cassette
capture is a separate opt-in maintenance operation; normal quality gates never refresh these inputs.

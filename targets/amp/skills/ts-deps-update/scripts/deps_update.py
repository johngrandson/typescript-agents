#!/usr/bin/env python3
"""Inventory and update explicitly scoped pnpm dependencies, auditing before scripts."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid
import tempfile

SKILLS_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPTS = next((SKILLS_ROOT / name / 'scripts' for name in ('deps-audit', 'ts-deps-audit') if (SKILLS_ROOT / name / 'scripts/audit_core.py').is_file()), None)
if AUDIT_SCRIPTS is None:
    print(json.dumps({'status': 'incomplete', 'error': 'The sibling deps-audit skill is required.'}))
    raise SystemExit(3)
sys.path.insert(0, str(AUDIT_SCRIPTS))
from audit_core import AuditError, CACHE, atomic_json, digest, gate_check, read_json, read_yaml, resolve_graph, safe_extract, utcnow
from analysis import semver
from transport import Fetcher


def inventory(root, graph, scopes, fixtures=None):
    output = []
    fixture = read_json(fixtures / 'outdated.json') if fixtures else None
    for importer in graph['importers']:
        if scopes and importer not in scopes:
            continue
        command = ['pnpm', '--workspace-root', 'outdated', '--format', 'json'] if importer == '.' else ['pnpm', '--filter', './' + importer, 'outdated', '--format', 'json']
        if fixture is not None:
            result = fixture.get(importer, {})
        else:
            proc = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=90)
            try:
                result = json.loads(proc.stdout)
            except ValueError as exc:
                raise AuditError('pnpm outdated returned invalid JSON for ' + importer) from exc
            if proc.returncode not in (0, 1) or not isinstance(result, dict) or 'error' in result:
                raise AuditError('pnpm outdated failed for ' + importer)
        if not isinstance(result, dict):
            raise AuditError('outdated JSON must map package names to version records')
        for occurrence in graph['occurrences']:
            if not occurrence['direct'] or occurrence['importer'] != importer or not occurrence['artifactId'] or occurrence.get('autoInstalledPeer'):
                continue
            artifact = next(a for a in graph['artifacts'] if a['id'] == occurrence['artifactId'])
            if artifact['kind'] != 'registry':
                continue
            value = result.get(occurrence['declaredName'])
            if value is None:
                continue
            if not isinstance(value, dict) or not all(isinstance(value.get(k), str) for k in ('current', 'wanted', 'latest')):
                raise AuditError('malformed outdated record for ' + occurrence['declaredName'])
            output.append({'importer': importer, 'declaredName': occurrence['declaredName'], 'realName': artifact['name'], 'section': occurrence['section'], 'specifier': occurrence['specifier'], 'locked': artifact['version'], 'wanted': value['wanted'], 'latest': value['latest'], 'peers': artifact['peerDependencies'], 'artifactId': artifact['id'], 'snapshot': occurrence['snapshot']})
    return output


def group_for(item):
    name = item['realName']
    importer = item['importer']
    if importer == 'apps/mobile' and (name in ('react', 'react-native', 'expo') or name.startswith('expo-') or name.startswith('@expo/')):
        family = 'expo-runtime'
    elif importer == 'apps/web' and (name in ('react', 'react-dom', 'next') or 'eslint-config-next' in name):
        family = 'next-runtime'
    elif name.startswith(('fastify', '@fastify/', '@sinclair/typebox')):
        family = 'api-contracts'
    elif name.startswith('drizzle-') or name in ('pg', 'postgres'):
        family = 'database'
    elif name.startswith(('vitest', '@vitest/')):
        family = 'tests'
    elif 'eslint' in name:
        family = 'lint'
    else:
        family = name
    return importer + ':' + family


def choose(items, packages, fetcher, graph):
    explicit = {}
    for request in packages:
        split = request.rfind('@')
        explicit[request[:split] if split > 0 else request] = request[split+1:] if split > 0 else None
    selected = []
    for item in items:
        key = item['declaredName'] if item['declaredName'] in explicit else item['realName']
        if explicit and key not in explicit:
            continue
        artifact = next(a for a in graph['artifacts'] if a['id'] == item['artifactId'])
        metadata = fetcher.metadata(artifact, packument=True)
        requested = explicit.get(key)
        requirement = item['specifier']
        if requirement.startswith('npm:'):
            requirement = requirement.rsplit('@', 1)[1]
        if requirement.startswith('catalog:'):
            catalog = requirement[8:]
            requirement = graph.get('catalogs', {}).get('catalog', {}).get(item['declaredName']) if not catalog else graph.get('catalogs', {}).get('catalogs', {}).get(catalog, {}).get(item['declaredName'])
            if not isinstance(requirement, str):
                raise AuditError('catalog declaration cannot be resolved')
        if requested:
            candidate = semver([{'op': 'select', 'versions': list(metadata.get('versions', {})), 'range': requested}])[0]
            if candidate != requested:
                raise AuditError('--pkg name@version requires an exact published stable version')
        else:
            # Default is the newest compatible patch, even when wanted points to a minor upgrade.
            series = '.'.join(item['locked'].split('.')[:2]) + '.x'
            candidate = semver([{'op': 'select', 'versions': list(metadata.get('versions', {})), 'range': series}])[0]
            if candidate and not semver([{'op': 'satisfies', 'version': candidate, 'range': requirement}])[0]:
                candidate = None
        if not candidate or candidate == item['locked']:
            continue
        meta = metadata['versions'][candidate]
        selected.append({**item, 'candidate': candidate, 'candidatePeers': meta.get('peerDependencies', {}), 'candidatePeersMeta': meta.get('peerDependenciesMeta', {}), 'group': group_for(item), 'explicitRequirementEdit': bool(requested), 'changelogSource': meta.get('repository') or metadata.get('repository'), 'candidateMetadataHash': digest(meta)})
    missing = set(explicit) - {item['declaredName'] for item in items} - {item['realName'] for item in items}
    if missing:
        raise AuditError('requested package absent from outdated inventory: ' + ', '.join(sorted(missing)))
    for item in selected:
        if not item['specifier'].startswith('catalog:'):
            continue
        consumers = {o['importer'] for o in graph['occurrences'] if o['direct'] and o['declaredName'] == item['declaredName'] and o['specifier'] == item['specifier']}
        included = {change['importer'] for change in selected if change['declaredName'] == item['declaredName'] and change['specifier'] == item['specifier'] and change['candidate'] == item['candidate']}
        if consumers != included:
            raise AuditError('shared catalog edit needs every affected consumer in the same compatible selected group')
    return selected


def check_candidate_peers(selected, graph):
    """Validate each consumer's actual peer choices before editing its requirements."""
    errors = []
    for item in selected:
        for peer, requirement in item['candidatePeers'].items():
            proposed = [change['candidate'] for change in selected if change['importer'] == item['importer'] and change['realName'] == peer]
            if not proposed:
                peer_ids = {o['artifactId'] for o in graph['occurrences'] if o['importer'] == item['importer'] and o['direct'] and o['declaredName'] == peer}
                proposed = [a['version'] for a in graph['artifacts'] if a['id'] in peer_ids]
            if not proposed:
                if item.get('candidatePeersMeta', {}).get(peer, {}).get('optional'):
                    continue
                errors.append({'importer': item['importer'], 'package': item['realName'], 'peer': peer, 'required': requirement, 'resolved': [], 'reason': 'No direct consumer peer; review the resolved peer snapshot before installation.'})
            elif not all(semver([{'op': 'satisfies', 'version': version, 'range': requirement} for version in proposed])):
                errors.append({'importer': item['importer'], 'package': item['realName'], 'peer': peer, 'required': requirement, 'resolved': proposed, 'reason': 'Select the minimum compatible consumer group.'})
    return errors


def changelog_evidence(selected, graph, fetcher):
    evidence = []
    for item in selected:
        current = next(a for a in graph['artifacts'] if a['id'] == item['artifactId'])
        for label, version in [('old', item['locked']), ('new', item['candidate'])]:
            artifact = dict(current, version=version)
            metadata = fetcher.metadata(artifact)
            if label == 'new':
                artifact['integrity'] = metadata.get('dist', {}).get('integrity')
                artifact['resolution'] = metadata.get('dist', {})
            body, algorithm = fetcher.tarball(artifact, metadata)
            with tempfile.TemporaryDirectory(prefix='ts-update-docs-') as directory:
                safe_extract(body, directory)
                package_root = Path(directory) / 'package'
                package = read_json(package_root / 'package.json')
                if package.get('name') != artifact['name'] or package.get('version') != version:
                    raise AuditError('changelog archive identity mismatch')
                documents = []
                for path in sorted(package_root.rglob('*')):
                    if path.is_file() and path.name.lower().startswith(('changelog', 'history', 'readme')):
                        if path.stat().st_size > 10 * 1024**2:
                            raise AuditError('changelog exceeds analysis limit')
                        documents.append({'file': path.relative_to(package_root).as_posix(), 'sha256': digest(path.read_bytes()), 'excerpt': '\n'.join(path.read_text(errors='replace').splitlines()[:100])})
                        if len(documents) >= 4:
                            break
                evidence.append({'importer': item['importer'], 'name': artifact['name'], 'version': version, 'state': label, 'url': metadata.get('dist', {}).get('tarball'), 'integrity': artifact['integrity'], 'metadataHash': digest(metadata), 'documents': documents, 'changelogStatus': 'available' if any(d['file'].lower().startswith(('changelog', 'history')) for d in documents) else 'unavailable_in_tarball; inspect official release notes before compatibility decisions'})
    return evidence


def execute(root, selected, report, run_dir, *, prepare_only=False):
    if (root / '.pnpmfile.cjs').exists():
        raise AuditError('.pnpmfile.cjs needs review/adaptation before a resolution can ignore or execute it')
    originals = {}
    paths = ['pnpm-lock.yaml', *sorted({str(Path(i['importer']) / 'package.json') for i in selected})]
    if any(item['specifier'].startswith('catalog:') for item in selected):
        paths.append('pnpm-workspace.yaml')
    for relative in paths:
        path = root / relative
        originals[relative] = path.read_bytes()
        backup = run_dir / 'before' / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(originals[relative])
    report['beforeHashes'] = {p: digest(data) for p, data in originals.items()}
    for relative in originals:
        if relative == 'pnpm-lock.yaml':
            continue
        path = root / relative
        if path.read_bytes() != originals[relative]:
            raise AuditError('manifest changed while preparing update: ' + relative)
        if relative == 'pnpm-workspace.yaml':
            import yaml
            configuration = read_yaml(path)
            for item in selected:
                if not item['specifier'].startswith('catalog:'):
                    continue
                name = item['specifier'][8:]
                catalog = configuration['catalog'] if not name else configuration['catalogs'][name]
                catalog[item['declaredName']] = item['candidate']
            # Serialize data only; YAML tags/hooks are never evaluated.
            serialized = yaml.safe_dump(configuration, sort_keys=False).encode()
            import os
            descriptor, temporary = tempfile.mkstemp(prefix='.workspace-', dir=path.parent)
            with os.fdopen(descriptor, 'wb') as output:
                output.write(serialized)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            continue
        manifest = read_json(path)
        for item in selected:
            if str(Path(item['importer']) / 'package.json') != relative:
                continue
            if item['specifier'].startswith('catalog:'):
                continue
            version = item['candidate']
            if item['specifier'].startswith('npm:'):
                version = 'npm:' + item['realName'] + '@' + version
            manifest[item['section']][item['declaredName']] = version
        atomic_json(path, manifest)
    commands = [['pnpm', 'install', '--lockfile-only', '--ignore-scripts', '--ignore-pnpmfile']]
    for command in commands:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=300)
        report['commands'].append({'argv': command, 'exitCode': result.returncode})
        if result.returncode:
            raise AuditError('lock preparation failed; review saved before-state and current manifests')
    if prepare_only:
        report['status'] = 'prepared'
        return 0
    auditor = AUDIT_SCRIPTS / 'deps_audit.py'
    command = [sys.executable, str(auditor), '--root', str(root), '--all', '--json']
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=900)
    report['commands'].append({'argv': command, 'exitCode': result.returncode})
    try:
        report['audit'] = json.loads(result.stdout)
    except ValueError as exc:
        raise AuditError('audit failed to produce a reviewable result') from exc
    if result.returncode or not gate_check(root, report['audit'].get('policy', {}).get('block_on_unvetted', 'new_only'))['allowed']:
        report['status'] = 'review_required'
        return result.returncode or 2
    # Audit and vetting cover the resolved lock before any package lifecycle execution.
    for command in [['pnpm', 'install', '--frozen-lockfile'], ['pnpm', 'verify']]:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=900)
        report['commands'].append({'argv': command, 'exitCode': result.returncode})
        if result.returncode:
            raise AuditError('verification/install failed; preserve the reviewable changes and diagnose before retrying')
    for importer in sorted({item['importer'] for item in selected} - {'.'}):
        scripts = read_json(root / importer / 'package.json').get('scripts', {})
        for script in ('build', 'test:run'):
            if script not in scripts:
                continue
            command = ['pnpm', '--filter', './' + importer, script]
            result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=900)
            report['commands'].append({'argv': command, 'exitCode': result.returncode})
            if result.returncode:
                raise AuditError('affected workspace verification failed: ' + importer)
    report['status'] = 'verified'
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--scope', action='append', default=[], help='exact importer path, e.g. apps/web')
    parser.add_argument('--pkg', action='append', default=[], help='name or name@exact-version')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--fixtures', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report = {'schemaVersion': 1, 'runId': uuid.uuid4().hex, 'startedAt': utcnow(), 'status': 'incomplete', 'commands': [], 'fixture': bool(args.fixtures)}
    code = 3
    run_dir = root / CACHE / 'runs' / ('update-' + report['runId'])
    try:
        graph = resolve_graph(root)
        if set(args.scope) - set(graph['importers']):
            raise AuditError('scope must be an exact lockfile importer')
        items = inventory(root, graph, args.scope, args.fixtures)
        report['inventory'] = items
        if args.dry_run:
            report['status'] = 'inventory'
            code = 0
        else:
            if args.fixtures:
                raise AuditError('fixture data is limited to inventory and cannot prepare real updates')
            fetcher = Fetcher(root, offline=args.offline)
            selected = choose(items, args.pkg, fetcher, graph)
            report['selected'] = selected
            report['peerCompatibility'] = check_candidate_peers(selected, graph)
            if report['peerCompatibility']:
                raise AuditError('candidate peers are incompatible or unresolved; review the recorded consumer group')
            if not selected:
                report['status'] = 'no_changes'
                code = 0
            else:
                run_dir.mkdir(parents=True, mode=0o700)
                report['changelogs'] = changelog_evidence(selected, graph, fetcher)
                atomic_json(run_dir / 'plan.json', report)
                code = execute(root, selected, report, run_dir, prepare_only=args.prepare_only)
    except (AuditError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        report['error'] = str(exc)
    report['completedAt'] = utcnow()
    report['exitCode'] = code
    atomic_json(run_dir / 'update.json', report)
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())

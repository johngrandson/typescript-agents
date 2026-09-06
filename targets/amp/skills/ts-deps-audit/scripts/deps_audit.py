#!/usr/bin/env python3
"""Read-only supply-chain audit for pnpm v9 projects; exit 0/2/3/64."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
import uuid

from audit_core import AuditError, CACHE, RULES, SCRIPTS, UnsafeArtifact, atomic_json, digest, finding, gate_check, graph_diff, input_hashes, read_json, resolve_graph, safe_extract, scanner_hashes, utcnow
from analysis import advisory_diff, distance, external_tools, inspect_artifact, markdown, normalized_advisories, sarif, semver
import ledger
from transport import Fetcher


class InvalidRequest(AuditError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InvalidRequest(message)


def parser():
    result = Parser(description=__doc__)
    result.add_argument('--root', type=Path, default=Path.cwd())
    modes = result.add_mutually_exclusive_group()
    modes.add_argument('--all', action='store_true')
    modes.add_argument('--base', metavar='REF')
    modes.add_argument('--preview', nargs='+', metavar='PACKAGE')
    result.add_argument('--quick', action='store_true')
    result.add_argument('--offline', action='store_true')
    result.add_argument('--fixtures', type=Path)
    result.add_argument('--no-differential', action='store_true')
    result.add_argument('--strict', action='store_true')
    result.add_argument('--ci', action='store_true')
    result.add_argument('--quiet', action='store_true')
    result.add_argument('--json', action='store_true')
    result.add_argument('--sarif', type=Path)
    result.add_argument('--gate-check', action='store_true')
    result.add_argument('--gate-mode', choices=('warn', 'new_only', 'strict', 'full'), default='new_only')
    llm = result.add_mutually_exclusive_group()
    llm.add_argument('--llm', action='store_true')
    llm.add_argument('--no-llm', action='store_true')
    result.add_argument('--trace', action='store_true')
    result.add_argument('--compressed-limit', type=int, default=100*1024**2)
    result.add_argument('--unpacked-limit', type=int, default=1024**3)
    result.add_argument('--members-limit', type=int, default=100000)
    result.add_argument('--text-limit', type=int, default=10*1024**2)
    return result


def empty_graph():
    return {'artifacts': [], 'occurrences': [], 'edges': [], 'importers': [], 'snapshots': {}}


def initial(args):
    return {'schemaVersion': 2, 'runId': uuid.uuid4().hex, 'startedAt': utcnow(), 'completedAt': None, 'mode': 'preview' if args.preview else 'all' if args.all else 'diff', 'scope': 'all' if args.all else 'changed', 'quick': args.quick, 'fixture': bool(args.fixtures), 'offline': args.offline or bool(args.fixtures), 'inputHashes': {}, 'toolHashes': {}, 'sources': {}, 'rules': {'native:' + rule: {'status': 'pending'} for rule in RULES}, 'coverage': {'artifacts_scanned': 0, 'limitations': [], 'exclusions': []}, 'artifacts': [], 'occurrences': [], 'findings': [], 'decisions': [], 'errors': [], 'status': 'incomplete', 'exitCode': 3, 'audit_passed': False, 'options': {'compressedLimit': args.compressed_limit, 'unpackedLimit': args.unpacked_limit, 'membersLimit': args.members_limit, 'textLimit': args.text_limit, 'differential': not args.no_differential}}


def git_base(root, ref, directory):
    if ref.startswith('-'):
        raise InvalidRequest('base ref cannot begin with a dash')
    commit = subprocess.run(['git', 'rev-parse', '--verify', ref + '^{commit}'], cwd=root, capture_output=True, text=True)
    if commit.returncode:
        raise AuditError('base ref does not resolve to a commit: ' + ref)
    commit = commit.stdout.strip()
    archive = subprocess.run(['git', 'archive', '--format=tar', commit], cwd=root, capture_output=True)
    if archive.returncode:
        raise AuditError('unable to read the declared base commit')
    safe_extract(archive.stdout, directory, compressed_limit=1024**3, unpacked_limit=2*1024**3)
    return commit


def preview_graph(graph, requested, fetcher):
    new = copy.deepcopy(graph)
    replacements, selected = {}, []
    for request in requested:
        split = request.rfind('@')
        explicit = request[split+1:] if split > 0 else None
        name = request[:split] if explicit else request
        occurrences = [o for o in graph['occurrences'] if o['direct'] and o['artifactId'] and (o['declaredName'] == name or next(a['name'] for a in graph['artifacts'] if a['id'] == o['artifactId']) == name)]
        if not occurrences and not explicit:
            raise InvalidRequest('package absent from project requires an explicit version: ' + name)
        if not occurrences:
            occurrences = [{'importer': '<preview>', 'section': 'dependencies', 'declaredName': name, 'specifier': explicit, 'snapshot': None, 'peers': [], 'artifactId': None, 'path': [name], 'direct': True, 'workspace': None}]
        for occurrence in occurrences:
            current = next((a for a in graph['artifacts'] if a['id'] == occurrence['artifactId']), None)
            if current is None:
                from audit_core import registry_config, registry_for
                registries = registry_config(fetcher.root)
                current = {'name': name, 'version': explicit, 'kind': 'registry', 'source': registry_for(name, registries), 'resolution': {}, 'integrity': None}
            if current['kind'] != 'registry':
                raise InvalidRequest('preview cannot update a workspace/local/external source as npm')
            packument = fetcher.metadata(current, packument=True)
            requirement = explicit or occurrence['specifier']
            if requirement.startswith('npm:'):
                requirement = requirement.rsplit('@', 1)[1]
            if requirement.startswith('catalog:'):
                catalog = requirement[8:]
                requirement = graph.get('catalogs', {}).get('catalog', {}).get(occurrence['declaredName']) if not catalog else graph.get('catalogs', {}).get('catalogs', {}).get(catalog, {}).get(occurrence['declaredName'])
            version = semver([{'op': 'select', 'versions': list(packument.get('versions', {})), 'range': requirement}])[0]
            if not version:
                raise AuditError('no stable candidate satisfies importer constraint')
            meta = packument['versions'][version]
            candidate = {**current, 'version': version, 'integrity': meta.get('dist', {}).get('integrity'), 'resolution': meta.get('dist', {})}
            candidate.pop('patchHash', None)
            candidate.pop('patchPath', None)
            candidate['id'] = digest(ledger.identity(candidate))
            replacements[(occurrence['importer'], occurrence['section'], occurrence['declaredName'], occurrence['artifactId'])] = candidate
            selected.append({'importer': occurrence['importer'], 'name': candidate['name'], 'specifier': occurrence['specifier'], 'candidate': version, 'peers': meta.get('peerDependencies', {}), 'resolution': 'candidate_only; resulting lock and peer compatibility require a new audit'})
            if occurrence['artifactId'] is None:
                new['occurrences'].append(occurrence)
    for occurrence in new['occurrences']:
        key = (occurrence['importer'], occurrence['section'], occurrence['declaredName'], occurrence['artifactId'])
        if key in replacements and occurrence['direct']:
            candidate = replacements[key]
            occurrence['artifactId'] = candidate['id']
            occurrence['snapshot'] = candidate['name'] + '@' + candidate['version']
            occurrence['peers'] = []
    ids = {o['artifactId'] for o in new['occurrences']}
    new['artifacts'] = list({a['id']: a for a in [*new['artifacts'], *replacements.values()] if a['id'] in ids}.values())
    return new, selected


def run(args, report):
    root = args.root.resolve()
    os.environ['TS_AUDIT_ROOT'] = str(root)
    if any(getattr(args, key) <= 0 for key in ('compressed_limit', 'unpacked_limit', 'members_limit', 'text_limit')):
        raise InvalidRequest('all resource limits must be positive')
    report['inputHashes'] = input_hashes(root)
    report['toolHashes'] = scanner_hashes(root)
    current = resolve_graph(root)
    report['coverage']['graphPaths'] = 'Occurrences carry one shortest path per direct consumer; edges preserve the complete dependency DAG including cycles.'
    report['sources']['lockfile'] = {'status': 'complete', 'required': True, 'expiresAt': time.time() + 600}
    fetcher = Fetcher(root, offline=args.offline, fixtures=args.fixtures, compressed_limit=args.compressed_limit)
    if fetcher.index:
        report['fixtureDetails'] = {'kind': fetcher.index['kind'], 'origin': fetcher.index['origin'], 'indexHash': digest((fetcher.fixtures / 'index.json').read_bytes())}
    with tempfile.TemporaryDirectory(prefix='ts-audit-' + report['runId'] + '-') as temp:
        temp = Path(temp)
        old, new = empty_graph(), current
        old_root = temp / 'old'
        if args.preview:
            old = current
            old_root = root
            new, report['candidates'] = preview_graph(current, args.preview, fetcher)
        elif not args.all:
            ref = args.base or 'HEAD'
            report['baseCommit'] = git_base(root, ref, old_root)
            report['baseRef'] = ref
            report['oldInputHashes'] = input_hashes(old_root)
            old = resolve_graph(old_root)
        diff = graph_diff(old, new)
        report.update({'diff': diff, 'artifacts': new['artifacts'], 'occurrences': new['occurrences'], 'edges': new['edges'], 'counts': {'artifacts': len(new['artifacts']), 'occurrences': len(new['occurrences']), 'importers': len(new['importers']), 'snapshots': len(new['snapshots'])}})
        if not args.all and not args.preview and not any(diff.values()) and report['oldInputHashes'] == report['inputHashes']:
            report.update(status='no_changes', exitCode=0)
            return
        # A graph-identical config/source edit still requires a fresh full scan.
        new_ids = {a['id'] for a in new['artifacts']} - {a['id'] for a in old['artifacts']}
        report['newArtifactIds'] = sorted(new_ids)
        selected_ids = {a['id'] for a in new['artifacts']} if args.all else {x[0] for changes in diff.values() for change in changes for x in change['new'] if x[0]}
        if not selected_ids:
            selected_ids = {a['id'] for a in new['artifacts']}
        # Advisories always examine the complete reachable destination graph.
        report['coverage']['selectedArtifacts'] = sorted(selected_ids)
        report['scope'] = 'all' if args.all else 'preview' if args.preview else 'changed'
        results = {}
        scan_artifacts = {a['id']: (a, root) for a in new['artifacts'] if a['id'] in selected_ids}
        if not args.no_differential and not args.quick:
            for artifact in old['artifacts']:
                if any(a['name'] == artifact['name'] and a['id'] in selected_ids for a in new['artifacts']):
                    scan_artifacts.setdefault(artifact['id'], (artifact, old_root))
        with ThreadPoolExecutor(max_workers=4) as pool:
            tasks = {}
            for key, (artifact, artifact_root) in scan_artifacts.items():
                task = pool.submit(fetcher.metadata, artifact) if args.quick else pool.submit(inspect_artifact, artifact, fetcher, temp / 'packages', artifact_root, args)
                tasks[task] = artifact
            for task in as_completed(tasks):
                artifact = tasks[task]
                try:
                    result = task.result()
                    if args.quick:
                        result = {'metadata': result, 'findings': [], 'publisher': {'status': 'unavailable'}}
                        if result['metadata'].get('deprecated'):
                            result['findings'].append(finding('registry:deprecation', 'WARN', artifact, 'Published version is deprecated', evidence={'reason': result['metadata']['deprecated']}))
                    results[artifact['id']] = result
                    if artifact['id'] in selected_ids:
                        report['findings'].extend(result['findings'])
                        artifact['coverage'] = {k: result[k] for k in ('inventory', 'archiveInventory', 'bundledDependencies', 'publisher', 'effectiveBytesHash') if k in result}
                        if not args.quick:
                            report['coverage']['artifacts_scanned'] += 1
                            report['coverage']['limitations'].extend(result['limitations'])
                            if result['parseFailures']:
                                report['errors'].append('TypeScript parse failures in ' + artifact['name'])
                                artifact['coverage']['parseFailures'] = result['parseFailures']
                except (AuditError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
                    report['errors'].append(artifact['name'] + ': ' + str(exc))
                    if isinstance(exc, UnsafeArtifact):
                        report['findings'].append(finding('source-change', 'BLOCK', artifact, str(exc)))
        if not args.quick:
            protected_path = SCRIPTS.parent / 'priv/protected-names.json'
            protected = read_json(protected_path)['names']
            for artifact in new['artifacts']:
                if artifact['id'] not in selected_ids:
                    continue
                previous = [a for a in old['artifacts'] if a['name'] == artifact['name']]
                if artifact['kind'] != 'registry' and artifact['id'] in new_ids:
                    report['findings'].append(finding('source-change', 'WARN', artifact, 'New external source requires review', evidence={'source': artifact['source']}))
                if any(a['version'] == artifact['version'] and a['source'] == artifact['source'] and a['integrity'] != artifact['integrity'] for a in previous):
                    report['findings'].append(finding('source-change', 'BLOCK', artifact, 'Integrity changed for an existing package version', evidence={'oldIntegrity': [a['integrity'] for a in previous if a['version'] == artifact['version']], 'newIntegrity': artifact['integrity']}))
                if previous and artifact['source'] not in {a['source'] for a in previous}:
                    report['findings'].append(finding('source-change', 'WARN', artifact, 'Package source changed', evidence={'old': sorted({a['source'] for a in previous}), 'new': artifact['source']}))
                if artifact['id'] in new_ids and not previous and artifact['name'] not in protected:
                    similar = [name for name in protected if distance(name, artifact['name']) <= 2 or name.split('/')[-1] == artifact['name'].split('/')[-1]]
                    if similar:
                        report['findings'].append(finding('name-similarity', 'WARN', artifact, 'New dependency resembles a protected direct dependency name', evidence={'similarNames': similar, 'meaning': 'similarity is a review signal, not proof of typosquatting'}))
                new_publisher = results.get(artifact['id'], {}).get('publisher', {})
                for before in previous:
                    old_publisher = results.get(before['id'], {}).get('publisher', {})
                    if old_publisher.get('status') == new_publisher.get('status') == 'available' and old_publisher['publisher'] != new_publisher['publisher']:
                        report['findings'].append(finding('publisher-change', 'WARN', artifact, 'Version publisher changed', evidence={'old': old_publisher, 'new': new_publisher}))
            config_artifact = {'id': '@project', 'name': '@project', 'version': 'working', 'source': 'project', 'integrity': None}
            for relative in report['inputHashes']:
                path = root / relative
                if relative.startswith('@') or not path.is_file():
                    continue
                text = path.read_text(errors='replace')
                for match in re.finditer('[\u202a-\u202e\u2066-\u2069]', text):
                    report['findings'].append(finding('bidi', 'BLOCK', config_artifact, 'Unicode bidirectional control in project configuration', relative, text.count('\n', 0, match.start()) + 1, text[max(0,match.start()-20):match.end()+20]))
            previous_findings = [f for a in old['artifacts'] for f in results.get(a['id'], {}).get('findings', [])]
            previous_keys = {f['fingerprint'] for f in previous_findings}
            current_keys = {f['fingerprint'] for f in report['findings']}
            for item in report['findings']:
                item['differential'] = 'carried' if not args.no_differential and item['fingerprint'] in previous_keys else 'new'
            if not args.no_differential:
                report['findings'].extend(dict(f, differential='dropped') for f in previous_findings if f['fingerprint'] not in current_keys)
            policy = ledger.load(root)[0]['policy']
            tools = external_tools(temp / 'packages', policy.get('required_tools', []) if policy.get('block_on_unvetted') == 'full' else [], fixture=args.offline or bool(args.fixtures))
            report['sources'].update({'optional:' + name: state for name, state in tools.items()})
            for name, state in tools.items():
                if state['status'] in ('failed', 'missing'):
                    report['errors'].append('optional scanner ' + name + ': ' + state['status'])
                if state['status'] == 'complete' and state.get('output'):
                    output = state['output']
                    # Preserve external scanner results and conservatively flag nonempty detections.
                    detections = output.get('results', []) if isinstance(output, dict) else output
                    if detections:
                        report['findings'].append(finding('external:' + name, 'WARN', config_artifact, 'Optional scanner reported findings requiring review', evidence={'results': detections}))
        exposures = {}
        advisory_raw = {}
        for label, graph, state_root in [('new', new, root), ('old', old, old_root)]:
            if label == 'old' and not old['artifacts']:
                exposures[label] = []
                continue
            try:
                raw = fetcher.advisories(graph, state_root, label)
                advisory_raw[label] = raw
                found, exposures[label] = normalized_advisories(raw, graph)
                if label == 'new':
                    report['findings'].extend(dict(f, differential='new') for f in found)
            except (AuditError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
                exposures[label] = []
                report['errors'].append('advisories ' + label + ': ' + str(exc))
                report['sources']['advisories:' + label] = {'status': 'failed', 'required': True}
        comparable = 'old' in advisory_raw and 'new' in advisory_raw
        # Both locks are compared to the union from this collection, avoiding temporal false introductions.
        if comparable:
            union = {'advisories': {str(index): item for index, item in enumerate([*advisory_raw['old'].get('advisories', {}).values(), *advisory_raw['new'].get('advisories', {}).values()])}}
            if union['advisories']:
                _, exposures['old'] = normalized_advisories(union, old)
                _, exposures['new'] = normalized_advisories(union, new)
        report['advisoryDiff'] = advisory_diff(exposures.get('old', []), exposures.get('new', []), old, new, comparable)
        report['sources'].update(fetcher.sources)
        # No-result data source is not "complete" merely because the loop ran.
        for rule in report['rules'].values():
            rule['status'] = 'skipped_quick' if args.quick else 'incomplete' if report['errors'] else 'complete'
        report['coverage']['limitations'] = sorted(set(report['coverage']['limitations']))
        report['findings'] = list({(f['artifactId'], f['fingerprint'], f.get('differential', 'new')): f for f in report['findings']}.values())
        artifact_context = {a['id']: a.get('contextHash') for a in new['artifacts']}
        for item in report['findings']:
            item['contextHash'] = artifact_context.get(item['artifactId'])
            item['evidenceHash'] = digest({'evidence': item['evidence'], 'contextHash': item['contextHash']})
        decision = ledger.apply(root, new['artifacts'], report['findings'], new_ids=new_ids)
        report['decisions'] = decision['applied']
        report['policy'] = decision['policy']
        report['unvetted'] = decision['unvetted']
        report['rejected'] = decision['rejected']
        active = [f for f in report['findings'] if f.get('differential') != 'dropped' and f.get('effectiveDecision', 'active') == 'active']
        report['score'] = sum({'BLOCK': 10, 'WARN': 3, 'INFO': 1}[f['severity']] for f in active)
        report['triageRequired'] = not args.no_llm and (args.llm or any(f['severity'] == 'BLOCK' for f in active) or report['score'] >= 9)
        report['triage'] = {'status': 'requested' if report['triageRequired'] else 'not_required', 'agent': 'npm-deps-triager', 'automaticSuppression': False}
        if input_hashes(root) != report['inputHashes'] or scanner_hashes(root) != report['toolHashes']:
            report['errors'].append('inputs or scanner changed during audit')
        blocked = bool(decision['unvetted'] or decision['rejected'] or any(f['severity'] == 'BLOCK' for f in active))
        if report['errors']:
            report.update(status='incomplete', exitCode=3)
        elif blocked:
            report.update(status='blocked', exitCode=2)
        elif active:
            report.update(status='findings', exitCode=2 if args.strict and any(f['severity'] == 'WARN' for f in active) else 0)
        else:
            report.update(status='clean', exitCode=0)
        report['audit_passed'] = report['exitCode'] == 0 and not (args.quick or args.preview or args.fixtures) and report['status'] in ('clean', 'findings')
        fetcher.clean_cache()


def main(argv=None):
    try:
        args = parser().parse_args(argv)
    except InvalidRequest as exc:
        print(json.dumps({'schemaVersion': 2, 'status': 'invalid_request', 'exitCode': 64, 'audit_passed': False, 'errors': [str(exc)]}))
        return 64
    if args.gate_check:
        result = gate_check(args.root.resolve(), args.gate_mode)
        print(json.dumps(result))
        return 0 if result['allowed'] else 2
    report = initial(args)
    root = args.root.resolve()
    last = root / CACHE / 'last-run.json'
    try:
        # Invalidate previous approval before any collection or graph parsing.
        atomic_json(last, report)
        run_directory = root / CACHE / 'runs' / report['runId']
        run_directory.mkdir(mode=0o700, parents=True)
    except OSError as exc:
        report['errors'].append('cannot write audit sidecar: ' + str(exc))
        print(json.dumps(report))
        return 3
    def interrupted(signum, frame):
        raise KeyboardInterrupt('audit interrupted')
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)
    try:
        run(args, report)
    except InvalidRequest as exc:
        report.update(status='invalid_request', exitCode=64, audit_passed=False)
        report['errors'].append(str(exc))
    except (AuditError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        report.update(status='incomplete', exitCode=3, audit_passed=False)
        report['errors'].append(str(exc) or 'audit interrupted')
    report['completedAt'] = utcnow()
    try:
        atomic_json(run_directory / 'report.json', report)
        (run_directory / 'report.md').write_text(markdown(report))
        if args.sarif:
            atomic_json(args.sarif, sarif(report))
        atomic_json(last, report)
    except OSError as exc:
        report.update(status='incomplete', exitCode=3, audit_passed=False)
        report['errors'].append('cannot publish audit outputs: ' + str(exc))
        # Initial incomplete sidecar remains when final publication fails.
        try:
            atomic_json(last, report)
        except OSError:
            pass
    if args.json:
        print(json.dumps(report, sort_keys=True))
    elif not args.quiet:
        print(markdown(report))
    return report['exitCode']


if __name__ == '__main__':
    raise SystemExit(main())

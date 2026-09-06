"""Static source inspection, advisory normalization and lossless renderers."""
from __future__ import annotations
import json
from pathlib import Path
import re
import shutil
import subprocess

from audit_core import AuditError, SCRIPTS, UnsafeArtifact, digest, finding, read_json, safe_extract


def semver(operations):
    proc = subprocess.run(['node', str(SCRIPTS / 'semver.cjs')], input=json.dumps(operations), capture_output=True, text=True, timeout=30)
    if proc.returncode:
        raise AuditError('semver parser unavailable or input range unsupported')
    return json.loads(proc.stdout)


def distance(left, right):
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j-1] + (a != b)))
        previous = current
    return previous[-1]


def scan_tree(directory, artifact, *, text_limit=10*1024**2):
    directory = Path(directory)
    findings, source_files, inventory, bundles, limitations = [], [], [], [], []
    entrypoints = set()
    manifest = read_json(directory / 'package.json') if (directory / 'package.json').exists() else {}
    def add_entries(value):
        if isinstance(value, str) and not value.startswith(('#', 'node:')):
            entrypoints.add(value.removeprefix('./'))
        elif isinstance(value, dict):
            for child in value.values():
                add_entries(child)
        elif isinstance(value, list):
            for child in value:
                add_entries(child)
    for key in ('bin', 'main', 'module', 'exports'):
        add_entries(manifest.get(key))
    for command in manifest.get('scripts', {}).values():
        for match in re.finditer(r'(?:^|[ ;&])node(?:\s+--[\w-]+)*\s+([\w./-]+)', command):
            entrypoints.add(match[1].removeprefix('./'))
    for file in sorted(directory.rglob('*')):
        if not file.is_file():
            continue
        relative = file.relative_to(directory).as_posix()
        data = file.read_bytes()
        item = {'path': relative, 'size': len(data), 'sha256': digest(data)}
        inventory.append(item)
        try:
            text = data.decode('utf-8')
            if '\x00' in text:
                raise UnicodeDecodeError('utf-8', data, 0, 1, 'NUL bytes')
        except UnicodeDecodeError:
            item['kind'] = 'binary'
            findings.append(finding('opaque-payload', 'WARN', artifact, 'Binary payload requires review', relative, evidence={'size': len(data), 'sha256': item['sha256']}))
            continue
        item['kind'] = 'text'
        if len(data) > text_limit:
            raise AuditError('text analysis limit exceeded: ' + relative)
        for match in re.finditer('[\u202a-\u202e\u2066-\u2069]', text):
            findings.append(finding('bidi', 'BLOCK', artifact, 'Unicode bidirectional control in package content', relative, text.count('\n', 0, match.start()) + 1, text[max(0, match.start()-30):match.end()+30], {'codepoint': hex(ord(match.group())), 'fixtureContext': bool(re.search(r'(?:test|fixture|example)', relative))}))
        for match in re.finditer(r'[A-Za-z0-9+/]{256,}={0,2}', text):
            findings.append(finding('opaque-payload', 'WARN', artifact, 'Large encoded payload requires review', relative, text.count('\n', 0, match.start()) + 1, match.group()[:80], {'length': len(match.group()), 'sha256': digest(match.group().encode())}))
        if re.search(r'\.[cm]?[jt]sx?$', file.name) or relative in entrypoints or text.startswith(('#!/usr/bin/env node', '#!/usr/bin/node')):
            source_files.append({'path': relative, 'text': text})
        if file.name == 'package.json':
            package = read_json(file)
            if relative != 'package.json':
                bundles.append({'path': relative, 'name': package.get('name'), 'version': package.get('version'), 'sha256': item['sha256']})
            for phase, command in package.get('scripts', {}).items():
                if phase in ('preinstall', 'install', 'postinstall', 'prepare'):
                    danger = bool(re.search(r'(?:curl|wget)\b.*(?:\||;|&&).*\b(?:sh|bash|node)\b|\brm\s+-rf', command))
                    findings.append(finding('lifecycle-effects', 'BLOCK' if danger else 'WARN', artifact, 'Lifecycle script is declared; its effects require review', relative, snippet=command, evidence={'phase': phase, 'executed': False, 'demonstratedDangerousChain': danger}))
            item['entrypoints'] = {key: package[key] for key in ('bin', 'main', 'module', 'exports', 'types', 'bundledDependencies', 'bundleDependencies') if key in package}
    try:
        proc = subprocess.run(['node', str(SCRIPTS / 'scan_source.cjs')], input=json.dumps({'files': source_files}), capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuditError('required TypeScript parser unavailable or timed out') from exc
    if proc.returncode:
        raise AuditError('required TypeScript parser failed; verify the directly installed typescript dependency')
    parsed = json.loads(proc.stdout)
    for item in parsed['findings']:
        findings.append(finding(item['rule'], item['severity'], artifact, item['message'], item['file'], item['line'], item['snippet'], item['evidence']))
    limitations.extend(parsed['limitations'])
    return {'findings': findings, 'inventory': inventory, 'bundledDependencies': bundles, 'limitations': limitations, 'parseFailures': parsed['failures'], 'parserVersion': parsed['parserVersion']}


def inspect_artifact(artifact, fetcher, temp, root, args):
    unpacked = Path(temp) / artifact['id']
    if artifact['kind'] == 'file':
        from audit_core import tree_hash, verify_sri
        local = Path(artifact['localPath'])
        expected = 'sha256-' + __import__('base64').b64encode(bytes.fromhex(tree_hash(local))).decode()
        if artifact['integrity'] != expected:
            raise UnsafeArtifact('local artifact changed during collection')
        metadata = {'name': artifact['name'], 'version': artifact['version'], 'dist': {}}
        algorithm = 'sha256'
        if local.is_dir():
            package_root = unpacked / 'package'
            shutil.copytree(local, package_root, ignore=shutil.ignore_patterns('.git'), symlinks=True)
            archive_inventory = []
        else:
            body = local.read_bytes()
            verify_sri(body, artifact['integrity'])
            archive_inventory = safe_extract(body, unpacked, compressed_limit=args.compressed_limit, unpacked_limit=args.unpacked_limit, members_limit=args.members_limit)
            package_root = unpacked / 'package'
        artifact['bytesHash'] = tree_hash(local)
    else:
        metadata = fetcher.metadata(artifact)
        body, algorithm = fetcher.tarball(artifact, metadata)
        archive_inventory = safe_extract(body, unpacked, compressed_limit=args.compressed_limit, unpacked_limit=args.unpacked_limit, members_limit=args.members_limit)
        package_root = unpacked / 'package'
    if not package_root.is_dir():
        raise UnsafeArtifact('npm archive lacks package/ root')
    # Resolve internal archive links to byte copies for analysis, never filesystem links.
    members = {item['path']: item for item in archive_inventory}
    for member in archive_inventory:
        if member['kind'] != 'link':
            continue
        current = member
        seen = set()
        while current['kind'] == 'link':
            if current['path'] in seen:
                raise AuditError('archive contains a cyclic internal link')
            seen.add(current['path'])
            target = current['resolvedTarget']
            current = members.get(target)
            if current is None:
                raise AuditError('archive link target is absent')
        if current['kind'] != 'file':
            raise AuditError('archive directory links require additional analysis')
        alias = unpacked / member['path']
        target = unpacked / current['path']
        if not alias.is_relative_to(package_root) or not target.is_relative_to(package_root):
            raise UnsafeArtifact('npm package link escapes its package root')
        alias.parent.mkdir(parents=True, exist_ok=True)
        alias.write_bytes(target.read_bytes())
        alias.chmod(0o600)
        member['analysisTarget'] = current['path']
    package = read_json(package_root / 'package.json')
    if package.get('name') != artifact['name'] or package.get('version') != artifact['version'] and not (artifact['kind'] == 'file' and artifact['version'].startswith('file:')):
        raise UnsafeArtifact('tarball package.json name/version does not match locked artifact')
    result = scan_tree(package_root, artifact, text_limit=args.text_limit)
    result['archiveInventory'] = archive_inventory
    if artifact.get('patchPath'):
        patch = Path(root) / artifact['patchPath']
        # git apply is a data transform in our private tempdir, not a package lifecycle command.
        for line in patch.read_text().splitlines():
            if line.startswith(('--- ', '+++ ')):
                filename = line[4:].split('\t')[0]
                if filename != '/dev/null' and (filename.startswith('/') or '..' in Path(filename).parts or '\\' in filename):
                    raise UnsafeArtifact('patch path escapes artifact')
        for flags in (['--check'], []):
            proc = subprocess.run(['git', 'apply', '--no-index', *flags, str(patch.resolve())], cwd=package_root, capture_output=True, timeout=30)
            if proc.returncode:
                raise AuditError('patch could not be applied to the verified artifact')
        effective = scan_tree(package_root, artifact, text_limit=args.text_limit)
        result['originalInventory'] = result['inventory']
        result['inventory'] = effective['inventory']
        result['findings'].extend(effective['findings'])
        result['parseFailures'].extend(effective['parseFailures'])
        result['effectiveBytesHash'] = digest(effective['inventory'])
    if algorithm == 'sha1':
        result['findings'].append(finding('source-change', 'WARN', artifact, 'Artifact uses legacy SHA-1 integrity'))
    if metadata.get('deprecated'):
        result['findings'].append(finding('registry:deprecation', 'WARN', artifact, 'Published version is deprecated', evidence={'reason': str(metadata['deprecated'])[:500]}))
    result['metadata'] = metadata
    result['publisher'] = {'status': 'available', 'publisher': metadata['_npmUser'], 'version': artifact['version']} if metadata.get('_npmUser') else {'status': 'unavailable'}
    result['directory'] = str(package_root)
    return result


def normalized_advisories(raw, graph):
    advisories = list(raw.get('advisories', {}).values())
    for name, value in raw.get('vulnerabilities', {}).items():
        for via in value.get('via', []):
            if isinstance(via, dict):
                advisories.append(dict(via, module_name=via.get('name', name), vulnerable_versions=via.get('range', value.get('range'))))
    findings, exposures, queries, matches = [], [], [], []
    for advisory in advisories:
        name = advisory.get('module_name') or advisory.get('name')
        affected = advisory.get('vulnerable_versions') or advisory.get('range')
        if not name or not affected:
            raise AuditError('advisory missing package name or affected range')
        for artifact in graph['artifacts']:
            if artifact['name'] == name:
                queries.append({'op': 'satisfies', 'version': artifact['version'], 'range': affected})
                matches.append((advisory, artifact))
    results = semver(queries) if queries else []
    for applies, (advisory, artifact) in zip(results, matches):
        if not applies:
            continue
        ids = set(advisory.get('cves') or []) | set(advisory.get('aliases') or [])
        if advisory.get('github_advisory_id'):
            ids.add(advisory['github_advisory_id'])
        if advisory.get('url'):
            match = re.search(r'GHSA-[\w-]+', advisory['url'])
            if match:
                ids.add(match.group())
        if not ids:
            ids.add(str(advisory.get('id') or advisory.get('source') or digest(advisory)))
        severity_name = advisory.get('severity', 'unknown').lower()
        severity = {'critical': 'BLOCK', 'high': 'BLOCK', 'moderate': 'WARN', 'medium': 'WARN', 'low': 'INFO'}.get(severity_name, 'WARN')
        occurrence_units = sorted({o['importer'] for o in graph['occurrences'] if o['artifactId'] == artifact['id']})
        evidence = {'identifiers': sorted(ids), 'affectedRange': advisory.get('vulnerable_versions') or advisory.get('range'), 'patchedVersions': advisory.get('patched_versions'), 'sourceUrl': advisory.get('url'), 'severity_unknown': severity_name == 'unknown', 'importers': occurrence_units}
        item = finding('advisory:' + sorted(ids)[0], severity, artifact, advisory.get('title') or 'Dependency advisory', evidence=evidence)
        findings.append(item)
        exposures.append({'identifiers': sorted(ids), 'name': artifact['name'], 'version': artifact['version'], 'importers': occurrence_units, 'artifactId': artifact['id']})
    return findings, exposures


def advisory_diff(old, new, old_graph, new_graph, comparable=True):
    # Merge aliases transitively so GHSA and CVE representations denote one advisory.
    groups = []
    for entry in old + new:
        current = set(entry['identifiers'])
        overlapping = [group for group in groups if group & current]
        for group in overlapping:
            current |= group
            groups.remove(group)
        groups.append(current)
    result = []
    for identifiers in groups:
        names = {e['name'] for e in old + new if identifiers & set(e['identifiers'])}
        for name in names:
            units = {'*'} | {i for e in old + new if e['name'] == name and identifiers & set(e['identifiers']) for i in e['importers']}
            for importer in sorted(units):
                def versions(entries):
                    return sorted({e['version'] for e in entries if e['name'] == name and identifiers & set(e['identifiers']) and (importer == '*' or importer in e['importers'])})
                before, after = versions(old), versions(new)
                if not before and not after:
                    continue
                present_ids = {o['artifactId'] for o in new_graph['occurrences'] if importer == '*' or o['importer'] == importer}
                still_present = any(a['name'] == name and (importer == '*' or a['id'] in present_ids) for a in new_graph['artifacts'])
                state = 'not_comparable' if not comparable else 'introduced' if after and not before else 'still_exposed' if after else 'patched' if still_present else 'removed'
                result.append({'identifiers': sorted(identifiers), 'name': name, 'importer': importer, 'status': state, 'exposed_versions_old': before, 'exposed_versions_new': after})
    return result


def sarif(report):
    findings = report['findings']
    rules = sorted({f['rule_id'] for f in findings})
    return {'version': '2.1.0', '$schema': 'https://json.schemastore.org/sarif-2.1.0.json', 'runs': [{'tool': {'driver': {'name': 'typescript-starter-deps-audit', 'rules': [{'id': rule} for rule in rules]}}, 'properties': {'runId': report['runId'], 'status': report['status'], 'fixture': report.get('fixture'), 'coverage': report.get('coverage')}, 'results': [{'ruleId': f['rule_id'], 'level': {'BLOCK': 'error', 'WARN': 'warning', 'INFO': 'note'}[f['severity']], 'message': {'text': f['message']}, 'partialFingerprints': {'native/v1': f['fingerprint']}, 'locations': [{'physicalLocation': {'artifactLocation': {'uri': f.get('file') or 'package.json'}, 'region': {'startLine': max(1, f.get('line', 1))}}}], 'properties': f} for f in findings]}]}


def markdown(report):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')[:300]
    lines = [f"# Dependency audit {report['runId']}", '', f"Status: {report['status']}. Mode: {report['mode']}. Scope: {report.get('scope', 'unresolved')}.", f"Artifacts: {len(report['artifacts'])}. Occurrences: {len(report['occurrences'])}. Audit passed: {report['audit_passed']}.", '']
    if report.get('fixture'):
        lines += ['Fixture run. Synthetic/captured test data cannot approve a real dependency gate.', '']
    lines += ['| Severity | Rule | Package | Location | State | Evidence |', '| --- | --- | --- | --- | --- | --- |']
    for f in report['findings']:
        lines.append('| ' + ' | '.join(cell(value) for value in (f['severity'], f['rule_id'], f['artifact'].get('name'), f"{f['file']}:{f['line']}", f.get('differential', 'new'), f['message'])) + ' |')
    for error in report['errors']:
        lines += ['', 'Incomplete: ' + cell(error)]
    for limitation in report['coverage'].get('limitations', []):
        lines += ['', 'Coverage: ' + cell(limitation)]
    return '\n'.join(lines) + '\n'


def external_tools(directory, required=(), *, fixture=False):
    results = {}
    commands = {'semgrep': ['semgrep', 'scan', '--json', '--config', str(SCRIPTS.parent / 'priv/semgrep/typescript-supply-chain.yaml'), str(directory)], 'yara': ['yara', '-r', str(SCRIPTS.parent / 'priv/yara/npm-malware.yar'), str(directory)], 'osv-scanner': ['osv-scanner', 'scan', 'source', '--format', 'json', '--recursive', str(directory)]}
    for tool, command in commands.items():
        available = shutil.which(tool)
        if not available:
            results[tool] = {'status': 'missing' if tool in required else 'unavailable', 'required': tool in required}
            continue
        # OSV source scanning can contact its database; explicit fixtures/offline never run it.
        if fixture and tool == 'osv-scanner':
            results[tool] = {'status': 'missing' if tool in required else 'unavailable', 'required': tool in required, 'reason': 'network is disabled'}
            continue
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=60, env={**__import__('os').environ, 'SEMGREP_SEND_METRICS': 'off', 'SEMGREP_ENABLE_VERSION_CHECK': '0'})
            if proc.returncode not in (0, 1):
                raise AuditError('tool returned an error')
            if tool != 'yara':
                output = json.loads(proc.stdout)
                if output.get('errors'):
                    raise AuditError('tool reported analysis errors')
            else:
                output = proc.stdout.splitlines()
            results[tool] = {'status': 'complete', 'required': tool in required, 'output': output, 'expiresAt': __import__('time').time() + 600}
        except (AuditError, OSError, ValueError, subprocess.TimeoutExpired):
            results[tool] = {'status': 'failed', 'required': tool in required}
    return results

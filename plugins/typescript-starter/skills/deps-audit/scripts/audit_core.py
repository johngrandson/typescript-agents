"""Safe pnpm v9 inventory, artifact verification and dependency gate contracts.

Only local data is read by this module. Package code is never imported/executed.
"""
from __future__ import annotations

import base64
from collections import deque
from datetime import datetime, timezone
import hashlib
import gzip
import io
import json
import os
import posixpath
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile
import time
import urllib.parse

import yaml

RULES = ['bidi', 'dynamic-eval', 'lifecycle-effects', 'decoded-execution', 'source-change', 'publisher-change', 'opaque-payload', 'name-similarity']
SECTIONS = ('dependencies', 'devDependencies', 'optionalDependencies')
SCRIPTS = Path(__file__).resolve().parent
CACHE = '.claude/deps-audit'


class AuditError(ValueError):
    """An input or coverage failure that cannot be interpreted as a clean scan."""


class UnsafeArtifact(AuditError):
    pass


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise AuditError(f'duplicate key: {key}')
        out[key] = value
    return out


def read_json(path):
    try:
        return json.loads(Path(path).read_text(), object_pairs_hook=unique_pairs)
    except (OSError, ValueError) as exc:
        raise AuditError(f'invalid JSON in {Path(path).name}: {exc}') from exc


class UniqueLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise AuditError('YAML aliases are unsupported; expand them explicitly')
        return super().compose_node(parent, index)


def mapping(loader, node):
    pairs = []
    for key, value in node.value:
        pairs.append((loader.construct_object(key), loader.construct_object(value, deep=True)))
    return unique_pairs(pairs)


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def read_yaml(path):
    try:
        raw = Path(path).read_text()
        if len(raw) > 32 * 1024 * 1024:
            raise AuditError('YAML exceeds 32 MiB input limit')
        result = yaml.load(raw, Loader=UniqueLoader)
        if not isinstance(result, dict):
            raise AuditError('YAML document must be a mapping')
        return result
    except (OSError, yaml.YAMLError, RecursionError) as exc:
        raise AuditError(f'invalid YAML in {Path(path).name}: {exc}') from exc


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(data, out, indent=2, sort_keys=True)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def confined(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise UnsafeArtifact(f'path escapes project: {relative}')
    return path


def tree_hash(path):
    path = Path(path)
    if path.is_symlink():
        raise UnsafeArtifact('local artifact symlinks are unsupported')
    if path.is_file():
        return digest(path.read_bytes())
    if not path.is_dir():
        raise AuditError(f'local artifact missing: {path.name}')
    entries = {}
    for file in sorted(path.rglob('*')):
        if '.git' in file.relative_to(path).parts:
            continue
        if file.is_symlink():
            raise UnsafeArtifact('local artifact contains a symlink')
        if file.is_file():
            entries[file.relative_to(path).as_posix()] = digest(file.read_bytes())
    return digest(entries)


def split_snapshot(value):
    """Separate balanced peer/patch suffixes, including nested peer snapshots."""
    if not isinstance(value, str) or not value:
        raise AuditError('snapshot key must be a nonempty string')
    start = value.find('(')
    if start < 0:
        return value, []
    suffixes, depth, begin = [], 0, start
    for index in range(start, len(value)):
        ch = value[index]
        if ch == '(':
            if depth == 0:
                begin = index + 1
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth < 0:
                raise AuditError(f'unbalanced snapshot: {value}')
            if depth == 0:
                suffixes.append(value[begin:index])
        elif depth == 0:
            raise AuditError(f'invalid snapshot suffix: {value}')
    if depth:
        raise AuditError(f'unbalanced snapshot: {value}')
    return value[:start], suffixes


def package_parts(value):
    base, peers = split_snapshot(value)
    if '@' not in base[1:]:
        raise AuditError(f'unrecognized package identity: {value}')
    name, version = base.rsplit('@', 1)
    return name, version, peers


def registry_config(root):
    registries = {'default': 'https://registry.npmjs.org/'}
    # User-level config is included for private registry routing, never reported raw.
    for path in (Path.home() / '.npmrc', root / '.npmrc'):
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith(('#', ';')) or '=' not in line:
                continue
            key, value = map(str.strip, line.split('=', 1))
            value = re.sub(r'\$\{([^}]+)\}', lambda m: os.environ.get(m[1], ''), value)
            if key == 'registry' or key.endswith(':registry'):
                parsed = urllib.parse.urlsplit(value)
                if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
                    raise AuditError('registry must be HTTPS without embedded credentials')
                registries['default' if key == 'registry' else key.split(':')[0]] = value.rstrip('/') + '/'
    override = os.environ.get('npm_config_registry') or os.environ.get('NPM_CONFIG_REGISTRY')
    if override:
        parsed = urllib.parse.urlsplit(override)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
            raise AuditError('environment registry must be HTTPS without credentials')
        registries['default'] = override.rstrip('/') + '/'
    return registries


def registry_for(name, registries):
    return registries.get(name.split('/')[0], registries['default'])


def input_hashes(root):
    root = Path(root).resolve()
    lock = read_yaml(root / 'pnpm-lock.yaml')
    paths = {'pnpm-lock.yaml', 'package.json', 'pnpm-workspace.yaml', '.npmrc', '.pnpmfile.cjs', 'dependency-vet.json', '.claude/deps-audit-policy.json'}
    for importer in lock.get('importers', {}):
        paths.add((Path(importer) / 'package.json').as_posix())
    for item in (lock.get('patchedDependencies') or {}).values():
        if isinstance(item, dict) and item.get('path'):
            paths.add(item['path'])
    workspace = read_yaml(root / 'pnpm-workspace.yaml') if (root / 'pnpm-workspace.yaml').exists() else {}
    for pattern in workspace.get('packages', []):
        if not isinstance(pattern, str) or pattern.startswith('!'):
            continue
        for manifest in root.glob(pattern.rstrip('/') + '/package.json'):
            paths.add(manifest.relative_to(root).as_posix())
    result = {}
    for relative in sorted(paths):
        path = confined(root, relative)
        result[relative] = digest(path.read_bytes()) if path.is_file() else None
    # Effective environment registry routing and user config are hashed, never copied into reports.
    user_config = Path.home() / '.npmrc'
    result['@user-npmrc'] = digest(user_config.read_bytes()) if user_config.exists() else None
    result['@registries'] = digest(registry_config(root))
    for importer, data in lock.get('importers', {}).items():
        for section in SECTIONS:
            for declaration in data.get(section, {}).values():
                value = declaration.get('version', '') if isinstance(declaration, dict) else ''
                if value.startswith('file:'):
                    result['@local:' + importer + ':' + value] = tree_hash(confined(root, str(Path(importer) / value[5:])))
    if (root / 'dependency-vet.json').exists():
        import ledger
        local, imported = ledger.load(root)
        references = [entry['path'] for entry in local['imports']]
        references.extend(reference.get('path') for entry in local['audits'] + imported for reference in entry['evidence'] if isinstance(reference, dict) and reference.get('path'))
        for reference in sorted(set(references)):
            path = confined(root, reference)
            result['@review-evidence:' + reference] = digest(path.read_bytes()) if path.is_file() else None
    for key, data in lock.get('packages', {}).items():
        _, version, _ = package_parts(key)
        if version.startswith('file:'):
            result['@local-snapshot:' + key] = tree_hash(confined(root, version[5:]))
    return result


def scanner_hashes(root=None):
    files = {p.name: digest(p.read_bytes()) for p in sorted(SCRIPTS.glob('*')) if p.suffix in ('.py', '.cjs', '.json')}
    for p in sorted((SCRIPTS.parent / 'priv').rglob('*')):
        if p.is_file():
            files[p.relative_to(SCRIPTS.parent).as_posix()] = digest(p.read_bytes())
    import subprocess
    environment = {**os.environ, 'TS_AUDIT_ROOT': str(root or Path.cwd())}
    proc = subprocess.run(['node', str(SCRIPTS / 'require_tool.cjs')], capture_output=True, text=True, env=environment, timeout=10)
    if proc.returncode:
        raise AuditError('required pinned TypeScript/semver tooling unavailable; set TS_AUDIT_TOOLING')
    for name, data in json.loads(proc.stdout).items():
        files[name + '/package.json'] = digest(Path(data['packagePath']).read_bytes())
        files[name + '/entry'] = digest(Path(data['entry']).read_bytes())
        library = Path(data['packagePath']).parent
        files[name + '/implementation'] = digest({p.relative_to(library).as_posix(): digest(p.read_bytes()) for p in sorted(library.rglob('*.js'))})
    return files


def resolve_graph(root):
    root = Path(root).resolve()
    lock = read_yaml(root / 'pnpm-lock.yaml')
    if str(lock.get('lockfileVersion')) != '9.0':
        raise AuditError(f'unsupported pnpm lockfile version: {lock.get("lockfileVersion")}')
    for key in ('importers', 'packages', 'snapshots'):
        if not isinstance(lock.get(key), dict):
            raise AuditError(f'lockfile requires {key} mapping')
    workspace = read_yaml(root / 'pnpm-workspace.yaml') if (root / 'pnpm-workspace.yaml').exists() else {}
    registries = registry_config(root)
    root_manifest = read_json(root / 'package.json')
    declared_overrides = workspace.get('overrides', root_manifest.get('pnpm', {}).get('overrides', {}))
    if declared_overrides != lock.get('overrides', {}):
        raise AuditError('configured overrides do not match lock overrides')
    manifests, workspace_paths = {}, set()
    for importer in lock['importers']:
        path = confined(root, importer)
        manifests[importer] = read_json(path / 'package.json')
        workspace_paths.add(path)
    for pattern in workspace.get('packages', []):
        if isinstance(pattern, str) and not pattern.startswith('!'):
            workspace_paths.update(p.parent.resolve() for p in root.glob(pattern + '/package.json'))
    artifacts, snapshots, edges, occurrences = {}, {}, [], []
    for snapshot, data in lock['snapshots'].items():
        base, peers = split_snapshot(snapshot)
        package_data = lock['packages'].get(base)
        # Some patched entries carry patch suffix in the packages key.
        if package_data is None:
            package_data = lock['packages'].get(snapshot)
        if not isinstance(package_data, dict):
            raise AuditError(f'unresolved package for snapshot: {snapshot}')
        resolution = package_data.get('resolution') or {}
        name, version, _ = package_parts(base)
        source = registry_for(name, registries)
        kind = 'registry'
        if resolution.get('repo') or resolution.get('commit') or version.startswith(('git', 'http')):
            kind, source = 'external', resolution.get('repo', version)
        elif version.startswith('file:'):
            kind, source = 'file', version
        elif resolution.get('tarball'):
            host = urllib.parse.urlsplit(resolution['tarball']).netloc
            if host != urllib.parse.urlsplit(source).netloc:
                kind, source = 'external', resolution['tarball']
        artifact = {'name': name, 'version': version, 'source': source, 'kind': kind, 'integrity': resolution.get('integrity'), 'resolution': resolution, 'os': package_data.get('os', []), 'cpu': package_data.get('cpu', []), 'optional': bool(package_data.get('optional')), 'peerDependencies': package_data.get('peerDependencies', {})}
        patch = (lock.get('patchedDependencies') or {}).get(base)
        if patch:
            if not isinstance(patch, dict) or not patch.get('path'):
                raise AuditError(f'unsupported patch declaration for {base}')
            patch_path = confined(root, patch['path'])
            artifact['patchHash'] = digest(patch_path.read_bytes())
            artifact['patchPath'] = patch['path']
        if kind == 'file':
            artifact['localPath'] = str(confined(root, version[5:]))
            if Path(artifact['localPath']) == root:
                raise AuditError('a file dependency cannot contain the audit project itself')
            if Path(artifact['localPath']).is_dir():
                local_manifest = read_json(Path(artifact['localPath']) / 'package.json')
                if local_manifest.get('name') != name:
                    raise UnsafeArtifact('local package name mismatch')
                artifact['version'] = local_manifest.get('version')
                if not isinstance(artifact['version'], str):
                    raise AuditError('local package requires a version string')
            artifact['integrity'] = 'sha256-' + base64.b64encode(bytes.fromhex(tree_hash(artifact['localPath']))).decode()
        artifact['id'] = digest({k: artifact.get(k) for k in ('name', 'version', 'source', 'integrity', 'patchHash')})
        artifacts[artifact['id']] = artifact
        snapshots[snapshot] = {'artifactId': artifact['id'], 'peers': peers, 'dependencies': data or {}}
    # Local snapshot paths can change bytes without any manifest/lock edit.
    # Their content hashes are also added by input_hashes below.
    # Inventory unreferenced package resolutions too, never discard an optional/platform entry.
    covered = {split_snapshot(s)[0] for s in snapshots}
    missing = set(lock['packages']) - covered
    if missing:
        raise AuditError('package resolutions lack snapshots: ' + ', '.join(sorted(missing)[:10]))

    def resolve(name, value, importer):
        if value.startswith(('link:', 'workspace:')):
            if value.startswith('link:'):
                path = confined(root, str(Path(importer) / value[5:]))
            else:
                matches = [confined(root, key) for key, manifest in manifests.items() if manifest.get('name') == name]
                if len(matches) != 1:
                    raise AuditError(f'workspace target is ambiguous or absent: {name}')
                path = matches[0]
            if path not in workspace_paths:
                raise UnsafeArtifact(f'link target outside declared workspace: {name}')
            local = read_json(path / 'package.json')
            if local.get('name') != name:
                raise UnsafeArtifact(f'workspace name mismatch: {name}')
            return None, path.relative_to(root).as_posix()
        candidate = value if value in snapshots else name + '@' + value
        if candidate not in snapshots:
            raise AuditError(f'unresolved dependency: {name} -> {value}')
        return candidate, None

    for key, node in snapshots.items():
        for section in ('dependencies', 'optionalDependencies'):
            for name, value in node['dependencies'].get(section, {}).items():
                target, local = resolve(name, str(value), '.')
                edges.append({'from': key, 'to': target, 'local': local, 'name': name, 'optional': section == 'optionalDependencies'})
    adjacency = {}
    for edge in edges:
        adjacency.setdefault(edge['from'], []).append(edge)
    for importer, data in lock['importers'].items():
        manifest = manifests[importer]
        for section in SECTIONS:
            declared = dict(manifest.get(section, {}))
            locked = data.get(section, {})
            auto_peers = {}
            if section == 'dependencies' and lock.get('settings', {}).get('autoInstallPeers'):
                for peer, constraint in manifest.get('peerDependencies', {}).items():
                    if peer in locked and not any(peer in manifest.get(s, {}) for s in SECTIONS):
                        declared[peer] = constraint
                        auto_peers[peer] = constraint
            if set(declared) != set(locked):
                raise AuditError(f'manifest/lock dependency mismatch: {importer} {section}')
            for name, item in locked.items():
                if not isinstance(item, dict) or 'specifier' not in item or 'version' not in item:
                    raise AuditError(f'invalid importer resolution: {importer}/{name}')
                specifier = declared[name]
                if specifier != item['specifier']:
                    override_matches = []
                    for selector, replacement in lock.get('overrides', {}).items():
                        selected_name = selector.rsplit('@', 1)[0] if '@' in selector[1:] else selector
                        if '>' not in selected_name and selected_name == name and replacement == item['specifier']:
                            override_matches.append(selector)
                    if not override_matches:
                        raise AuditError(f'manifest/lock specifier mismatch: {importer}/{name}')
                if str(specifier).startswith('catalog:'):
                    catalog_name = str(specifier)[8:]
                    catalog = workspace.get('catalog', {}) if not catalog_name else workspace.get('catalogs', {}).get(catalog_name, {})
                    if name not in catalog:
                        raise AuditError(f'unresolved catalog for {name}')
                target, local = resolve(name, str(item['version']), importer)
                if str(specifier).startswith('catalog:'):
                    constraint = catalog[name]
                    if isinstance(constraint, str) and constraint.startswith('npm:'):
                        constraint = constraint.rsplit('@', 1)[1]
                    if target and isinstance(constraint, str) and not constraint.startswith(('workspace:', 'link:', 'file:')):
                        from analysis import semver
                        artifact = artifacts[snapshots[target]['artifactId']]
                        if not semver([{'op': 'satisfies', 'version': artifact['version'], 'range': constraint}])[0]:
                            raise AuditError(f'catalog constraint does not match locked version: {importer}/{name}')
                    elif not isinstance(constraint, str):
                        raise AuditError('catalog constraint must be a string')
                queue = deque([(target, [name], local)])
                visited = set()
                while queue:
                    current, path, local = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    node = snapshots.get(current, {})
                    occurrences.append({'importer': importer, 'section': section, 'declaredName': name, 'specifier': specifier, 'snapshot': current, 'peers': node.get('peers', []), 'artifactId': node.get('artifactId'), 'workspace': local, 'path': path, 'direct': len(path) == 1, 'autoInstalledPeer': name in auto_peers})
                    for edge in adjacency.get(current, []):
                        queue.append((edge['to'], path + [edge['name']], edge['local']))
                    if len(occurrences) > 200000:
                        raise AuditError('graph exceeds 200000 occurrence limit')
    contexts = {}
    for occurrence in occurrences:
        if occurrence['artifactId']:
            contexts.setdefault(occurrence['artifactId'], []).append({k: occurrence.get(k) for k in ('importer', 'section', 'declaredName', 'specifier', 'snapshot', 'workspace')})
    for artifact in artifacts.values():
        artifact['contextHash'] = digest(sorted(contexts.get(artifact['id'], []), key=lambda o: json.dumps(o, sort_keys=True)))
    return {'artifacts': sorted(artifacts.values(), key=lambda a: a['id']), 'occurrences': occurrences, 'edges': edges, 'importers': sorted(manifests), 'snapshots': snapshots, 'overrides': lock.get('overrides', {}), 'catalogs': {k: workspace[k] for k in ('catalog', 'catalogs') if k in workspace}}


def graph_diff(old, new):
    def units(graph):
        out = {}
        for o in graph['occurrences']:
            key = (o['importer'], o['section'], o['declaredName'], tuple(o['path']))
            out.setdefault(key, set()).add((o['artifactId'], o['snapshot'], o['workspace']))
        return out
    before, after = units(old), units(new)
    result = {key: [] for key in ('added', 'removed', 'artifact_changed', 'resolution_changed')}
    for key in sorted(before.keys() | after.keys()):
        left, right = before.get(key, set()), after.get(key, set())
        if left == right:
            continue
        kind = 'added' if not left else 'removed' if not right else 'resolution_changed' if {x[0] for x in left} == {x[0] for x in right} else 'artifact_changed'
        result[kind].append({'importer': key[0], 'section': key[1], 'declaredName': key[2], 'path': list(key[3]), 'old': sorted(left, key=str), 'new': sorted(right, key=str)})
    return result


def verify_sri(data, integrity):
    supported = {'sha512': 3, 'sha384': 2, 'sha256': 1, 'sha1': 0}
    candidates = []
    for token in str(integrity or '').split():
        algorithm, sep, encoded = token.partition('-')
        if sep and algorithm in supported:
            candidates.append((supported[algorithm], algorithm, encoded.split('?')[0]))
    if not candidates:
        raise UnsafeArtifact('missing supported artifact integrity')
    strongest = max(x[0] for x in candidates)
    for strength, algorithm, encoded in candidates:
        if strength != strongest:
            continue
        try:
            expected = base64.b64decode(encoded, validate=True)
        except ValueError:
            continue
        if hashlib.new(algorithm, data).digest() == expected:
            return algorithm
    raise UnsafeArtifact('artifact integrity mismatch')


def safe_extract(data, destination, *, compressed_limit=100*1024**2, unpacked_limit=1024**3, members_limit=100000):
    if len(data) > compressed_limit:
        raise AuditError('compressed artifact limit exceeded')
    if data.startswith(b'\x1f\x8b'):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
                expanded = stream.read(unpacked_limit + 1)
            if len(expanded) > unpacked_limit:
                raise AuditError('unpacked archive byte limit exceeded')
            data = expanded
        except (gzip.BadGzipFile, EOFError, OSError) as exc:
            raise AuditError('invalid or truncated gzip archive') from exc
    if data.startswith((b'BZh', b'\xfd7zXZ\x00')):
        raise AuditError('only gzip and bounded uncompressed tar archives are supported')
    if len(data) > unpacked_limit:
        raise AuditError('unpacked archive byte limit exceeded')
    destination = Path(destination)
    inventory, seen, total = [], set(), 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
            members = []
            for member in archive:
                if len(members) >= members_limit:
                    raise AuditError('archive member limit exceeded')
                name = PurePosixPath(member.name)
                if name.is_absolute() or '..' in name.parts or '\\' in member.name or not name.parts:
                    raise UnsafeArtifact('archive path traversal or absolute path')
                normalized = name.as_posix().rstrip('/')
                if normalized in seen:
                    raise UnsafeArtifact('duplicate archive member')
                seen.add(normalized)
                if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                    raise UnsafeArtifact('archive contains a device or unsupported member')
                if member.issym() or member.islnk():
                    target = PurePosixPath(member.linkname)
                    combined = name.parent / target if member.issym() else target
                    depth = 0
                    if target.is_absolute() or '\\' in member.linkname:
                        raise UnsafeArtifact('archive link escapes root')
                    for part in combined.parts:
                        depth += -1 if part == '..' else 0 if part == '.' else 1
                        if depth < 0:
                            raise UnsafeArtifact('archive link escapes root')
                total += member.size
                if member.size < 0 or total > unpacked_limit:
                    raise AuditError('unpacked artifact limit exceeded')
                members.append(member)
            # Refuse files under any link, even though links are not materialized.
            links = {PurePosixPath(m.name) for m in members if m.issym() or m.islnk()}
            files = {PurePosixPath(m.name) for m in members if m.isfile()}
            for member in members:
                name = PurePosixPath(member.name)
                if any(parent in links or parent in files for parent in name.parents):
                    raise UnsafeArtifact('archive member beneath a link or regular file')
            destination.mkdir(parents=True, exist_ok=True, mode=0o700)
            for member in members:
                item = {'path': member.name, 'size': member.size, 'kind': 'file' if member.isfile() else 'directory' if member.isdir() else 'link'}
                if member.isfile():
                    file = destination / member.name
                    file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    raw = archive.extractfile(member).read()
                    if len(raw) != member.size:
                        raise AuditError('truncated archive member')
                    file.write_bytes(raw)
                    file.chmod(0o600)
                    item['sha256'] = digest(raw)
                elif member.issym() or member.islnk():
                    item['target'] = member.linkname
                    item['resolvedTarget'] = posixpath.normpath(str(PurePosixPath(member.name).parent / member.linkname) if member.issym() else member.linkname)
                inventory.append(item)
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise AuditError(f'invalid or truncated archive: {type(exc).__name__}') from exc
    return inventory


def finding(rule, severity, artifact, message, file='', line=1, snippet='', evidence=None, confidence='high'):
    result = {'rule_id': 'native:' + rule if ':' not in rule else rule, 'severity': severity, 'artifactId': artifact.get('id'), 'artifact': {k: artifact.get(k) for k in ('name', 'version', 'source', 'integrity', 'patchHash')}, 'file': file, 'line': line, 'snippet': snippet[:300], 'message': message, 'evidence': evidence or {}, 'confidence': confidence}
    # Stable across line movement and versions for differential comparison; ledger also checks artifact identity.
    result['fingerprint'] = digest({k: result[k] for k in ('rule_id', 'file', 'snippet', 'message')} | {'package': artifact.get('name')})
    result['evidenceHash'] = digest(result['evidence'])
    return result


def gate_check(root, mode='new_only'):
    root = Path(root)
    try:
        report = read_json(root / CACHE / 'last-run.json')
        if report.get('schemaVersion') != 2 or report.get('audit_passed') is not True:
            raise AuditError('a complete real audit is required')
        if report.get('status') not in ('clean', 'findings') or report.get('quick') or report.get('fixture') or report.get('mode') == 'preview':
            raise AuditError('audit mode cannot satisfy the gate')
        age = time.time() - timestamp(report['completedAt'])
        if age < 0 or age > 600:
            raise AuditError('audit is stale; maximum age is ten minutes')
        if input_hashes(root) != report.get('inputHashes') or scanner_hashes(root) != report.get('toolHashes'):
            raise AuditError('lock, configuration, ledger or scanner changed')
        if mode in ('strict', 'full') and report.get('scope') != 'all':
            raise AuditError('policy requires --all')
        for source in report.get('sources', {}).values():
            if source.get('required') and (source.get('status') != 'complete' or source.get('expiresAt', 0) <= time.time()):
                raise AuditError('required source is missing or stale')
            if source.get('cachePath'):
                cached = read_json(confined(root / CACHE, source['cachePath']))
                body = base64.b64decode(cached['body'], validate=True)
                if digest(body) != source.get('sha256') or cached.get('sha256') != source.get('sha256'):
                    raise AuditError('cached source evidence changed')
        if report.get('baseCommit'):
            import subprocess
            ref = report.get('baseRef', 'HEAD')
            current = subprocess.run(['git', 'rev-parse', '--verify', ref + '^{commit}'], cwd=root, capture_output=True, text=True)
            if current.returncode or current.stdout.strip() != report['baseCommit']:
                raise AuditError('audit base changed')
        import ledger
        import copy
        current_findings = copy.deepcopy(report.get('findings', []))
        policy = ledger.apply(root, report.get('artifacts', []), current_findings, new_ids=set(report.get('newArtifactIds', [a['id'] for a in report.get('artifacts', [])])))
        if policy['unvetted'] or policy['rejected'] or any(f['severity'] == 'BLOCK' and f.get('differential') != 'dropped' and f.get('effectiveDecision', 'active') == 'active' for f in current_findings):
            raise AuditError('dependency reviews no longer satisfy current policy')
        # Verify cached artifact bytes again. Cached findings never substitute for integrity.
        for artifact in report.get('artifacts', []):
            if artifact.get('cachePath'):
                path = confined(root / CACHE, artifact['cachePath'])
                verify_sri(path.read_bytes(), artifact['integrity'])
                marker = read_json(path.parent / 'complete.json')
                if marker.get('integrity') != artifact['integrity'] or marker.get('sha256') != artifact.get('bytesHash'):
                    raise AuditError('artifact cache is incomplete or changed')
                if digest(path.read_bytes()) != artifact.get('bytesHash'):
                    raise AuditError('artifact cache changed')
        return {'allowed': True, 'reason': 'complete audit matches the current inputs', 'runId': report['runId']}
    except (AuditError, OSError, KeyError, TypeError, ValueError) as exc:
        return {'allowed': False, 'reason': str(exc), 'command': 'python3 <deps-audit>/scripts/deps_audit.py --root . --all'}

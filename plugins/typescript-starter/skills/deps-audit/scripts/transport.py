"""Bounded registry/cassette reads, verified cache and advisory collection."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from audit_core import AuditError, CACHE, UnsafeArtifact, atomic_json, confined, digest, read_json, verify_sri


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AuditError('HTTP redirect refused; configure the final authorized origin')


class Fetcher:
    def __init__(self, root, *, offline=False, fixtures=None, compressed_limit=100*1024**2):
        self.root = Path(root)
        self.cache = self.root / CACHE / 'cache'
        self.cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.cache.chmod(0o700)
        self.offline = offline or fixtures is not None
        self.fixtures = Path(fixtures).resolve() if fixtures else None
        self.index = read_json(self.fixtures / 'index.json') if self.fixtures else None
        if self.index and (self.index.get('kind') not in ('synthetic', 'captured') or not self.index.get('origin') or not isinstance(self.index.get('files'), dict)):
            raise AuditError('fixture index requires kind, origin and file hashes')
        self.compressed_limit = compressed_limit
        self.rate_lock = threading.Lock()
        self.next_request = 0.0
        self.sources = {}

    def fixture_file(self, relative):
        path = confined(self.fixtures, relative)
        body = path.read_bytes()
        if self.index['files'].get(relative) != digest(body):
            raise AuditError(f'fixture hash mismatch: {relative}')
        return body

    def token_for(self, url):
        parsed = urllib.parse.urlsplit(url)
        request_key = '//' + parsed.netloc + parsed.path
        values = {}
        for file in (Path.home() / '.npmrc', self.root / '.npmrc'):
            if not file.exists():
                continue
            for line in file.read_text().splitlines():
                if '=' not in line or line.lstrip().startswith(('#', ';')):
                    continue
                key, value = map(str.strip, line.split('=', 1))
                if key.endswith(':_authToken') and request_key.startswith(key[:-11]):
                    value = re.sub(r'\$\{([^}]+)\}', lambda match: os.environ.get(match[1], ''), value)
                    if value:
                        values[key[:-11]] = value
                    else:
                        values.pop(key[:-11], None)
        return values[max(values, key=len)] if values else None

    def request(self, url, limit):
        if self.offline:
            raise AuditError('network is disabled')
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password or not parsed.netloc:
            raise AuditError('only HTTPS URLs without embedded credentials are supported')
        with self.rate_lock:
            delay = self.next_request - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self.next_request = time.monotonic() + 0.2
        headers = {'Accept': 'application/json', 'User-Agent': 'typescript-starter-deps-audit/1'}
        token = self.token_for(url)
        if token:
            headers['Authorization'] = 'Bearer ' + token
        try:
            with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url, headers=headers), timeout=30) as response:
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise AuditError('HTTP response exceeds configured byte limit')
                return body
        except urllib.error.HTTPError as exc:
            raise AuditError(f'registry HTTP {exc.code}; source unavailable') from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise AuditError(f'registry request failed: {type(exc).__name__}') from exc

    def metadata(self, artifact, *, packument=False):
        source = artifact['source']
        if artifact['kind'] != 'registry':
            # External artifacts use their exact locked resolution, without npm fallback.
            return {'name': artifact['name'], 'version': artifact['version'], 'dist': artifact['resolution'], '_publisherStatus': 'unavailable'}
        key = source + '|' + artifact['name'] + ('@*' if packument else '@' + artifact['version'])
        source_key = 'metadata:' + digest(key)
        if self.fixtures:
            relative = self.index.get('metadata', {}).get(key)
            if not relative:
                raise AuditError('fixture metadata missing for ' + artifact['name'])
            body = self.fixture_file(relative)
            fetched = time.time()
        else:
            cache = self.cache / 'metadata' / (digest(key) + '.json')
            entry = read_json(cache) if cache.exists() else None
            if entry and entry.get('fetchedAt', 0) + 86400 > time.time():
                body = base64.b64decode(entry['body'])
                if digest(body) != entry['sha256']:
                    raise AuditError('metadata cache hash mismatch')
                fetched = entry['fetchedAt']
            else:
                if self.offline:
                    raise AuditError('offline metadata missing or stale for ' + artifact['name'])
                url = source + urllib.parse.quote(artifact['name'], safe='@')
                if not packument:
                    url += '/' + urllib.parse.quote(artifact['version'], safe='')
                body = self.request(url, 32 * 1024**2)
                fetched = time.time()
                atomic_json(cache, {'body': base64.b64encode(body).decode(), 'sha256': digest(body), 'fetchedAt': fetched})
        try:
            data = json.loads(body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise AuditError('registry metadata is invalid JSON') from exc
        if not packument and (data.get('name') != artifact['name'] or data.get('version') != artifact['version']):
            raise UnsafeArtifact('registry metadata name/version mismatch')
        self.sources[source_key] = {'status': 'complete', 'required': True, 'sha256': digest(body), 'expiresAt': fetched + 86400, 'fixture': bool(self.fixtures), 'cachePath': cache.relative_to(self.root / CACHE).as_posix() if not self.fixtures else None}
        return data

    def tarball(self, artifact, metadata):
        integrity = artifact.get('integrity')
        if not integrity:
            raise UnsafeArtifact('locked artifact has no verifiable integrity')
        cache_key = digest(integrity)
        cache = self.cache / 'tarballs' / cache_key
        complete = cache / 'complete.json'
        target = cache / 'artifact.tgz'
        if self.fixtures:
            relative = self.index.get('tarballs', {}).get(integrity)
            if not relative:
                raise AuditError('fixture tarball missing for ' + artifact['name'])
            body = self.fixture_file(relative)
        elif complete.is_file() and target.is_file():
            marker = read_json(complete)
            body = target.read_bytes()
            if marker.get('integrity') != integrity or marker.get('sha256') != digest(body):
                raise UnsafeArtifact('artifact cache marker or bytes mismatch')
        else:
            if self.offline:
                raise AuditError('offline tarball missing or cache incomplete for ' + artifact['name'])
            url = artifact['resolution'].get('tarball') or metadata.get('dist', {}).get('tarball')
            if not url:
                raise AuditError('no exact tarball URL for ' + artifact['name'])
            body = self.request(url, self.compressed_limit)
        algorithm = verify_sri(body, integrity)
        if len(body) > self.compressed_limit:
            raise AuditError('compressed artifact limit exceeded')
        # Fixture reads never pollute production cache or make real offline approval possible.
        if not self.fixtures:
            cache.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd, temp = tempfile.mkstemp(prefix='.artifact-', dir=cache)
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(body)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temp, target)
                atomic_json(complete, {'integrity': integrity, 'sha256': digest(body), 'lastUsedAt': time.time()})
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
            artifact['cachePath'] = target.relative_to(self.root / CACHE).as_posix()
        artifact['bytesHash'] = digest(body)
        return body, algorithm

    def advisories(self, graph, state_root, label):
        identity = digest({'artifacts': [a['id'] for a in graph['artifacts']], 'registries': [a['source'] for a in graph['artifacts']]})
        source_key = 'advisories:' + label
        if self.fixtures:
            relative = self.index.get('advisories', {})
            if isinstance(relative, dict):
                relative = relative.get(label)
            if not relative:
                raise AuditError('fixture advisories missing')
            body = self.fixture_file(relative)
            fetched = time.time()
        else:
            cache = self.cache / 'advisories' / (identity + '.json')
            entry = read_json(cache) if cache.exists() else None
            if entry and entry.get('fetchedAt', 0) + 3600 > time.time():
                body = base64.b64decode(entry['body'])
                fetched = entry['fetchedAt']
                if entry.get('sha256') != digest(body):
                    raise AuditError('advisory cache hash mismatch')
            else:
                if self.offline:
                    raise AuditError('offline advisory data missing or stale')
                if not shutil.which('pnpm'):
                    raise AuditError('pnpm is required for advisory collection')
                with tempfile.TemporaryDirectory(prefix='ts-audit-advisories-') as directory:
                    target = Path(directory)
                    for relative in ('pnpm-lock.yaml', 'pnpm-workspace.yaml', '.npmrc', 'package.json'):
                        source = Path(state_root) / relative
                        if source.is_file():
                            destination = target / relative
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(source, destination)
                    for importer in graph['importers']:
                        if importer == '.':
                            continue
                        relative = Path(importer) / 'package.json'
                        destination = target / relative
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(Path(state_root) / relative, destination)
                    proc = subprocess.run(['pnpm', 'audit', '--json'], cwd=target, capture_output=True, timeout=90, env={**os.environ, 'npm_config_ignore_scripts': 'true'})
                    body = proc.stdout
                    try:
                        parsed = json.loads(body)
                    except ValueError as exc:
                        raise AuditError('pnpm audit returned no valid JSON') from exc
                    if proc.returncode not in (0, 1) or 'error' in parsed or not any(k in parsed for k in ('advisories', 'vulnerabilities', 'metadata')):
                        raise AuditError('pnpm audit source failed')
                fetched = time.time()
                atomic_json(cache, {'body': base64.b64encode(body).decode(), 'sha256': digest(body), 'fetchedAt': fetched})
        parsed = json.loads(body)
        if not isinstance(parsed, dict) or 'error' in parsed:
            raise AuditError('advisory source is invalid or failed')
        self.sources[source_key] = {'status': 'complete', 'required': True, 'sha256': digest(body), 'expiresAt': fetched + 3600, 'fixture': bool(self.fixtures), 'cachePath': cache.relative_to(self.root / CACHE).as_posix() if not self.fixtures else None}
        return parsed

    def clean_cache(self):
        cutoff = time.time() - 30 * 86400
        # Evidence is a sibling of cache and cannot be removed here.
        for marker in (self.cache / 'tarballs').glob('*/complete.json'):
            try:
                if read_json(marker).get('lastUsedAt', 0) < cutoff:
                    shutil.rmtree(marker.parent)
            except AuditError:
                continue

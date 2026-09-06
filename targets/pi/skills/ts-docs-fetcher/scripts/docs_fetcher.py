#!/usr/bin/env python3
"""Find focused documentation from verified locked package bytes or an explicit official URL."""
from __future__ import annotations
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.parse

SKILLS_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPTS = next((SKILLS_ROOT / name / 'scripts' for name in ('deps-audit', 'ts-deps-audit') if (SKILLS_ROOT / name / 'scripts/audit_core.py').is_file()), None)
if AUDIT_SCRIPTS is None:
    print(json.dumps({'status': 'incomplete', 'error': 'The sibling deps-audit skill is required.'}))
    raise SystemExit(3)
sys.path.insert(0, str(AUDIT_SCRIPTS))
from audit_core import AuditError, CACHE, atomic_json, digest, read_json, resolve_graph, safe_extract, utcnow
from transport import Fetcher


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.ignore = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'nav'):
            self.ignore += 1
        if tag in ('p', 'h1', 'h2', 'h3', 'li', 'pre', 'br'):
            self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav'):
            self.ignore = max(0, self.ignore - 1)
    def handle_data(self, data):
        if not self.ignore:
            self.parts.append(data)


def excerpt(text, query, lines=80):
    content = text.splitlines()
    if not query:
        return '\n'.join(content[:lines])
    relevant = [index for index, line in enumerate(content) if query.casefold() in line.casefold()]
    keep = sorted({i for index in relevant for i in range(max(0, index-3), min(len(content), index+8))})[:lines]
    return '\n'.join(f'{i+1}: {content[i]}' for i in keep)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--importer', default='.')
    parser.add_argument('--query', default='')
    parser.add_argument('--slug', default='dependency-research')
    parser.add_argument('--url', help='explicit official documentation URL; paths are never guessed')
    parser.add_argument('--url-version', help='version the official page explicitly documents')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--fixtures', type=Path)
    args = parser.parse_args()
    report = {'status': 'incomplete', 'fetchedAt': utcnow(), 'package': args.package, 'importer': args.importer, 'documents': [], 'fixture': bool(args.fixtures)}
    root = args.root.resolve()
    code = 3
    try:
        if not re.fullmatch('[a-zA-Z0-9_-]+', args.slug):
            raise AuditError('slug must use letters, digits, underscores or hyphens')
        graph = resolve_graph(root)
        matches = [o for o in graph['occurrences'] if o['direct'] and o['importer'] == args.importer and o['declaredName'] == args.package and o['artifactId']]
        if len(matches) != 1:
            raise AuditError('select one exact package occurrence with --importer')
        artifact = next(a for a in graph['artifacts'] if a['id'] == matches[0]['artifactId'])
        report['version'] = artifact['version']
        report['artifact'] = artifact
        target = root / '.claude/plans' / args.slug / 'research/docs'
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        fetcher = Fetcher(root, offline=args.offline, fixtures=args.fixtures)
        if args.url:
            parsed = urllib.parse.urlsplit(args.url)
            if parsed.scheme != 'https' or not parsed.netloc:
                raise AuditError('official documentation URL must use HTTPS')
            cache = root / CACHE / 'cache/docs' / (digest({'url': args.url, 'version': artifact['version']}) + '.json')
            cached = read_json(cache) if cache.exists() else None
            if cached and (args.offline or cached['fetchedAt'] + 86400 > time.time()):
                body = cached['body']
                if digest(body.encode()) != cached['sha256']:
                    raise AuditError('documentation cache integrity mismatch')
                fetched = cached['fetchedAt']
            else:
                body = fetcher.request(args.url, 10*1024**2).decode('utf-8')
                fetched = time.time()
                if '<html' in body.lower():
                    html = TextHTML()
                    html.feed(body)
                    body = ''.join(html.parts)
                atomic_json(cache, {'body': body, 'sha256': digest(body.encode()), 'fetchedAt': fetched, 'url': args.url})
            report['documents'].append({'url': args.url, 'version': args.url_version, 'freshness': 'stale' if fetched + 86400 <= time.time() else 'fresh', 'sha256': digest(body.encode()), 'excerpt': excerpt(body, args.query), 'limitation': None if args.url_version == artifact['version'] else 'This page is unversioned or documents a different version; applicability to the locked version needs verification.'})
        else:
            metadata = fetcher.metadata(artifact)
            body, _ = fetcher.tarball(artifact, metadata)
            with tempfile.TemporaryDirectory(prefix='ts-docs-') as directory:
                safe_extract(body, directory)
                package_root = Path(directory) / 'package'
                package = read_json(package_root / 'package.json')
                if package.get('name') != artifact['name'] or package.get('version') != artifact['version']:
                    raise AuditError('documentation tarball identity mismatch')
                candidates = []
                for file in package_root.rglob('*'):
                    if file.is_file() and (file.name.lower().startswith(('readme', 'changelog', 'history')) or file.name.endswith(('.d.ts', '.d.mts', '.d.cts')) or file.suffix in ('.ts', '.tsx', '.js', '.mjs', '.cjs', '.md')):
                        candidates.append(file)
                candidates.sort(key=lambda p: (not p.name.lower().startswith(('readme', 'changelog')), '.d.' not in p.name, p.as_posix()))
                for file in candidates:
                    if file.stat().st_size > 10*1024**2:
                        raise AuditError('documentation file exceeds text limit')
                    text = file.read_text(errors='replace')
                    selected = excerpt(text, args.query)
                    if selected:
                        report['documents'].append({'url': metadata.get('dist', {}).get('tarball'), 'file': file.relative_to(package_root).as_posix(), 'version': artifact['version'], 'freshness': 'immutable_verified_artifact', 'sha256': digest(file.read_bytes()), 'excerpt': selected})
                    if len(report['documents']) >= 12:
                        break
        if not report['documents']:
            report['status'] = 'no_matching_documentation'
        else:
            report['status'] = 'complete'
            code = 0
        destination = target / (re.sub('[^a-zA-Z0-9_.-]', '_', args.package) + '-' + digest({'query': args.query, 'version': artifact['version'], 'url': args.url})[:12] + '.json')
        atomic_json(destination, report)
        report['evidencePath'] = str(destination)
    except (AuditError, OSError, ValueError, KeyError) as exc:
        report['error'] = str(exc)
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())

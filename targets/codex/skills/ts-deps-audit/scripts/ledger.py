"""Strict, exact-identity dependency review records with durable evidence."""
from __future__ import annotations
from contextlib import contextmanager
import fcntl
from pathlib import Path
import time

from audit_core import AuditError, CACHE, atomic_json, confined, digest, read_json, timestamp

CRITERIA = {'safe_to_run', 'safe_to_deploy', 'does_not_implement_crypto', 'provenance_baseline'}
DECISIONS = {'observed', 'cleared', 'accepted_risk', 'rejected', 'revoked'}


def identity(artifact):
    return {key: artifact.get(key) for key in ('source', 'name', 'version', 'integrity', 'patchHash')}


def empty():
    return {'schemaVersion': 1, 'policy': {'block_on_unvetted': 'new_only', 'criteria_required': 'safe_to_deploy'}, 'audits': [], 'imports': []}


def validate(value):
    if not isinstance(value, dict) or value.get('schemaVersion') != 1:
        raise AuditError('unsupported dependency-vet.json schema')
    if not isinstance(value.get('policy'), dict) or not isinstance(value.get('audits'), list) or not isinstance(value.get('imports'), list):
        raise AuditError('ledger requires policy, audits and imports')
    policy = value['policy']
    if policy.get('block_on_unvetted', 'warn') not in ('warn', 'new_only', 'strict', 'full') or policy.get('criteria_required', 'safe_to_deploy') not in CRITERIA:
        raise AuditError('invalid dependency vet policy')
    seen = set()
    for entry in value['audits']:
        if not isinstance(entry, dict) or not all(k in entry for k in ('artifact', 'criteria', 'decision', 'reviewer', 'reviewedAt', 'reason', 'evidence', 'findingFingerprints')):
            raise AuditError('incomplete ledger audit entry')
        if not isinstance(entry['artifact'], dict) or not all(entry['artifact'].get(k) for k in ('source', 'name', 'version', 'integrity')):
            raise AuditError('audit requires exact source, name, version and integrity')
        if not isinstance(entry['criteria'], list) or not entry['criteria'] or not set(entry['criteria']) <= CRITERIA:
            raise AuditError('unknown or absent review criterion')
        if entry['decision'] not in DECISIONS:
            raise AuditError('unknown audit decision')
        reviewer = entry['reviewer']
        if not isinstance(reviewer, dict) or reviewer.get('kind') not in ('human', 'agent') or not reviewer.get('id'):
            raise AuditError('reviewer must identify the actual human or agent')
        try:
            reviewed = timestamp(entry['reviewedAt'])
        except (TypeError, ValueError) as exc:
            raise AuditError('invalid review timestamp') from exc
        if reviewed > time.time() + 60:
            raise AuditError('review timestamp is in the future')
        if not isinstance(entry['reason'], str) or not entry['reason'].strip() or not isinstance(entry['evidence'], list) or not isinstance(entry['findingFingerprints'], list):
            raise AuditError('review requires reason, evidence and finding fingerprints')
        if entry['decision'] == 'accepted_risk' and not entry.get('authorization'):
            raise AuditError('accepted_risk requires an explicit authorization reference')
        if entry['decision'] != 'accepted_risk' and entry.get('authorization'):
            raise AuditError('authorization is only valid for accepted_risk')
        if entry.get('id') in seen:
            raise AuditError('duplicate review id')
        if entry.get('id'):
            seen.add(entry['id'])
    for entry in value['imports']:
        if not isinstance(entry, dict) or not all(entry.get(k) for k in ('path', 'sha256', 'attribution')):
            raise AuditError('ledger import requires path, digest and attribution')
    return value


def load(root, *, imports=True):
    root = Path(root)
    file = root / 'dependency-vet.json'
    value = validate(read_json(file)) if file.exists() else {'schemaVersion': 1, 'policy': {'block_on_unvetted': 'warn', 'criteria_required': 'safe_to_deploy'}, 'audits': [], 'imports': []}
    imported = []
    if imports:
        for entry in value['imports']:
            path = confined(root, entry['path'])
            if digest(path.read_bytes()) != entry['sha256']:
                raise AuditError('pinned ledger import digest mismatch')
            other = validate(read_json(path))
            imported.extend(dict(audit, importedFrom=entry['attribution']) for audit in other['audits'])
            # Deliberately ignore nested imports: imports grant no transitive trust.
    return value, imported


@contextmanager
def locked(root):
    root = Path(root)
    directory = root / CACHE
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / 'ledger.lock').open('a') as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        yield
        fcntl.flock(file, fcntl.LOCK_UN)


def write(root, value):
    validate(value)
    atomic_json(Path(root) / 'dependency-vet.json', value)


def evidence_valid(root, entry):
    if not entry.get('evidence'):
        return False
    for reference in entry['evidence']:
        try:
            path = confined(Path(root), reference['path'])
            if digest(path.read_bytes()) != reference['sha256']:
                return False
        except (AuditError, KeyError, OSError, TypeError):
            return False
    return True


def applicable(root, artifact, entries, criterion):
    matches = [e for e in entries if identity(e['artifact']) == identity(artifact) and criterion in e['criteria']]
    # Local rejection/revocation beats imported approvals regardless of chronology.
    local = [e for e in matches if not e.get('importedFrom')]
    if local:
        matches = local
    matches.sort(key=lambda e: timestamp(e['reviewedAt']), reverse=True)
    return matches


def apply(root, artifacts, findings, *, new_ids=None):
    value, imported = load(root)
    entries = value['audits'] + imported
    criterion = value['policy'].get('criteria_required', 'safe_to_deploy')
    mode = value['policy'].get('block_on_unvetted', 'warn')
    applied, unvetted, rejected = [], [], []
    for artifact in artifacts:
        reviews = applicable(root, artifact, entries, criterion)
        latest = reviews[0] if reviews else None
        fresh = latest and time.time() - timestamp(latest['reviewedAt']) <= 90 * 86400 and evidence_valid(root, latest)
        if latest and latest['decision'] in ('rejected', 'revoked'):
            rejected.append(artifact['id'])
        trusted = fresh and latest['decision'] in ('cleared', 'accepted_risk') and latest.get('contextHash') == artifact.get('contextHash')
        relevant = mode in ('strict', 'full') or mode == 'new_only' and artifact['id'] in (new_ids or set())
        if relevant and not trusted:
            unvetted.append(artifact['id'])
        for item in findings:
            if item['artifactId'] != artifact['id'] or item.get('differential') == 'dropped':
                continue
            item['effectiveDecision'] = 'active'
            if trusted and item['fingerprint'] in latest['findingFingerprints'] and latest.get('findingEvidence', {}).get(item['fingerprint']) == item.get('evidenceHash'):
                # Evidence has exact identity and criterion; never erase original severity.
                item['effectiveDecision'] = latest['decision']
                item['reviewId'] = latest.get('id')
                applied.append({'fingerprint': item['fingerprint'], 'reviewId': latest.get('id'), 'decision': latest['decision']})
    return {'policy': value['policy'], 'applied': applied, 'unvetted': unvetted, 'rejected': rejected}


def append(root, entry):
    with locked(root):
        path = Path(root) / 'dependency-vet.json'
        value = validate(read_json(path)) if path.exists() else empty()
        comparable = {k: v for k, v in entry.items() if k not in ('id', 'reviewedAt', 'supersedes')}
        for previous in value['audits']:
            if {k: v for k, v in previous.items() if k not in ('id', 'reviewedAt', 'supersedes')} == comparable:
                return previous, False
        earlier = [a for a in value['audits'] if identity(a['artifact']) == identity(entry['artifact'])]
        if earlier:
            entry['supersedes'] = earlier[-1].get('id')
        entry['id'] = digest(entry)
        value['audits'].append(entry)
        write(root, value)
        return entry, True

#!/usr/bin/env python3
"""Record actual dependency review evidence without inventing user approval."""
from pathlib import Path
import argparse
import json
import sys

SKILLS_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPTS = next((SKILLS_ROOT / name / 'scripts' for name in ('deps-audit', 'ts-deps-audit') if (SKILLS_ROOT / name / 'scripts/audit_core.py').is_file()), None)
if AUDIT_SCRIPTS is None:
    print(json.dumps({'status': 'incomplete', 'error': 'The sibling deps-audit skill is required.'}))
    raise SystemExit(3)
sys.path.insert(0, str(AUDIT_SCRIPTS))
from audit_core import AuditError, CACHE, atomic_json, digest, read_json, resolve_graph, utcnow
import ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--seed', action='store_true')
    mode.add_argument('--list', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--artifact', help='exact artifact id from an audit report')
    mode.add_argument('--import-file', type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--attribution')
    parser.add_argument('--decision', choices=sorted(ledger.DECISIONS), default='observed')
    parser.add_argument('--criterion', action='append', choices=sorted(ledger.CRITERIA))
    parser.add_argument('--reason')
    parser.add_argument('--finding', action='append', default=[])
    parser.add_argument('--authorization', help='reference to explicit existing user authorization')
    parser.add_argument('--reviewer', default='agent:codex')
    parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.list:
            value, imported = ledger.load(root)
            result = {'audits': value['audits'], 'importedAudits': imported}
        elif args.import_file:
            if not args.sha256 or not args.attribution:
                raise AuditError('--import-file requires --sha256 and --attribution')
            body = args.import_file.read_bytes()
            if digest(body) != args.sha256:
                raise AuditError('import digest mismatch')
            ledger.validate(read_json(args.import_file))
            target = root / CACHE / 'evidence' / ('import-' + args.sha256 + '.json')
            atomic_json(target, read_json(args.import_file))
            # Pin the durable canonical bytes, while proving the requested source digest first.
            record = {'path': target.relative_to(root).as_posix(), 'sha256': digest(target.read_bytes()), 'sourceSha256': args.sha256, 'attribution': args.attribution}
            with ledger.locked(root):
                value = ledger.load(root, imports=False)[0] if (root / 'dependency-vet.json').exists() else ledger.empty()
                if record not in value['imports']:
                    value['imports'].append(record)
                ledger.write(root, value)
            result = record
        else:
            graph = resolve_graph(root)
            if args.seed:
                evidence = {'kind': 'inventory', 'createdAt': utcnow(), 'artifacts': [ledger.identity(a) for a in graph['artifacts']]}
                # Stable inventory permits repeated seed to be a no-op.
                target = root / CACHE / 'evidence' / ('inventory-' + digest(evidence['artifacts']) + '.json')
                if not target.exists():
                    atomic_json(target, evidence)
                new = 0
                with ledger.locked(root):
                    if not (root / 'dependency-vet.json').exists():
                        ledger.write(root, ledger.empty())
                for artifact in graph['artifacts']:
                    entry = {'artifact': ledger.identity(artifact), 'criteria': ['provenance_baseline'], 'decision': 'observed', 'reviewer': {'kind': 'agent', 'id': 'codex'}, 'reviewedAt': utcnow(), 'reason': 'Resolved identity inventoried from the current pnpm lock. No safety approval granted.', 'findingFingerprints': [], 'evidence': [{'path': target.relative_to(root).as_posix(), 'sha256': digest(target.read_bytes()), 'limitations': ['Inventory only; package bytes were not reviewed.']}]}
                    _, added = ledger.append(root, entry)
                    new += added
                result = {'observed': len(graph['artifacts']), 'newRecords': new, 'approved': 0}
            elif args.check:
                value, imported = ledger.load(root)
                criterion = value['policy'].get('criteria_required', 'safe_to_deploy')
                result = {'missing': [], 'stale': [], 'revoked': [], 'discrepant': []}
                current = {digest(ledger.identity(a)) for a in graph['artifacts']}
                for artifact in graph['artifacts']:
                    entries = ledger.applicable(root, artifact, value['audits'] + imported, criterion)
                    if not entries or entries[0]['decision'] == 'observed':
                        result['missing'].append(artifact['id'])
                    elif entries[0]['decision'] in ('revoked', 'rejected'):
                        result['revoked'].append(artifact['id'])
                    elif __import__('time').time() - __import__('audit_core').timestamp(entries[0]['reviewedAt']) > 90 * 86400 or not ledger.evidence_valid(root, entries[0]):
                        result['stale'].append(artifact['id'])
                result['discrepant'] = [e.get('id') for e in value['audits'] if digest(ledger.identity(e['artifact'])) not in current]
            else:
                if not args.reason or not args.criterion or not args.run:
                    raise AuditError('recording a review requires --reason, --criterion and --run')
                if args.decision == 'accepted_risk' and not args.authorization:
                    raise AuditError('accepted_risk requires --authorization referencing explicit authorization')
                report = read_json(args.run)
                if report.get('schemaVersion') != 2 or report.get('fixture') or report.get('status') in ('incomplete', 'invalid_request', 'no_changes'):
                    raise AuditError('review evidence must be a completed real audit')
                artifact = next((a for a in graph['artifacts'] if a['id'] == args.artifact), None)
                audited = next((a for a in report['artifacts'] if a['id'] == args.artifact), None)
                if artifact is None or audited is None or ledger.identity(artifact) != ledger.identity(audited) or artifact.get('contextHash') != audited.get('contextHash'):
                    raise AuditError('artifact does not match the current lock and audit')
                reviewed_findings = {f['fingerprint']: f for f in report['findings'] if f['artifactId'] == args.artifact and f.get('differential') != 'dropped'}
                if not set(args.finding) <= reviewed_findings.keys():
                    raise AuditError('finding fingerprint is absent from this artifact audit')
                kind, sep, reviewer = args.reviewer.partition(':')
                if not sep or kind not in ('human', 'agent') or not reviewer:
                    raise AuditError('--reviewer must identify actual human:id or agent:id')
                evidence = root / CACHE / 'evidence' / (report['runId'] + '.json')
                atomic_json(evidence, report)
                entry = {'artifact': ledger.identity(artifact), 'contextHash': artifact.get('contextHash'), 'criteria': args.criterion, 'decision': args.decision, 'reviewer': {'kind': kind, 'id': reviewer}, 'reviewedAt': utcnow(), 'reason': args.reason, 'findingFingerprints': args.finding, 'findingEvidence': {key: reviewed_findings[key]['evidenceHash'] for key in args.finding}, 'evidence': [{'path': evidence.relative_to(root).as_posix(), 'sha256': digest(evidence.read_bytes()), 'runId': report['runId'], 'rules': report['rules'], 'limitations': report['coverage'].get('limitations', [])}]}
                if args.authorization:
                    entry['authorization'] = args.authorization
                result, _ = ledger.append(root, entry)
        print(json.dumps(result, indent=2))
        return 2 if args.check and any(result.values()) else 0
    except (AuditError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({'status': 'incomplete', 'error': str(exc)}))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())

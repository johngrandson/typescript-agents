# Schema and imports

`dependency-vet.json` has `schemaVersion: 1`, `policy`, `audits` and `imports`. Every audit records
exact `artifact`, nonempty `criteria`, `decision`, `{kind,id}` reviewer, real UTC `reviewedAt`,
concrete `reason`, durable hashed `evidence` and `findingFingerprints`. Finding decisions also
record `findingEvidence`. `accepted_risk` alone requires `authorization`. New revisions link
`supersedes` and preserve prior records.

The seed policy is `{ "block_on_unvetted": "new_only", "criteria_required": "safe_to_deploy" }`.
Baseline observations do not satisfy it. A complete review may approve the artifact for the
requested criterion, but only listed exact fingerprints can change individual effective finding
decisions.

Imports require an explicit source file, expected SHA-256 and attribution:

```bash
python3 "../scripts/deps_vet.py" --root "$PWD" \
  --import-file reviewed-ledger.json --sha256 EXPECTED_DIGEST --attribution 'Reviewed source and revision'
```

The CLI verifies the input digest, copies canonical bytes into durable evidence and pins their
digest. To import a URL, first obtain the explicitly authorized file and verify the expected digest;
the ledger never silently refreshes remote trust. Nested imports are ignored. No trusted imports
ship with the plugin. A changed digest requires reviewing the ledger diff before recording a new
import.

Malformed schema, duplicate keys, unknown criteria, fabricated future timestamps, missing
authorizations and inconsistent identities fail validation. Evidence must remain inside the project
and its digest must match. Stale or missing evidence cannot satisfy the gate.

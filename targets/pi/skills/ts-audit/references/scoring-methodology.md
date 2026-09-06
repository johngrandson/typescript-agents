# Scoring methodology

Each category has 100 points. Report deductions with file/line or command evidence, never from keyword matches alone. Uninspected categories are UNKNOWN and prevent a complete overall health score.

| Category | Criteria and points |
| --- | --- |
| Architecture | Contract ownership 25, naming 15, dependency direction 15, module cohesion 15, runtime cycle safety 15, workspace conventions 15 |
| Performance | Confirmed SQL count 30, query indexes 20, bounded projections 15, event-loop health 15, UI retention 10, payload size 10 |
| Security | Critical defects absent 30, high defects absent 20, required permission boundaries 15, input validation 10, output/path safety 10, secret handling 15 |
| Test quality | Relevant behavior coverage 30, deterministic async 20, isolated state 15, reliable teardown 15, measured runtime 10, error paths 10 |
| Dependencies | Reviewed advisories 40, integrity/lifecycle audit 20, compatibility 20, unused deps 10, resolved version policy 10 |

Start each inspected criterion at its available points and deduct by actual impact: critical consumes the criterion, high half, medium one quarter, low one tenth. Show rounding and
avoid duplicate deductions for the same root cause. Absence of installed authentication is a stated capability limit; score a permission defect only against the actual requested
protection/deployment requirement.

`overall = architecture * .20 + performance * .25 + security * .25 + test_quality * .15 + dependencies * .15`

Grades: A 90–100, B 80–89, C 70–79, D 60–69, F below 60. A verified critical vulnerability, hardcoded secret, failed typecheck or failing required test overrides the numeric grade
with CRITICAL. Skipped/unavailable gates cannot be presented as healthy.

Use pnpm verify, targeted repository/client/worker tests, dependency audit evidence and real profiles. Preserve all command exit statuses; do not pipe away a failure or use a
successful dependency audit as a substitute for application security review.

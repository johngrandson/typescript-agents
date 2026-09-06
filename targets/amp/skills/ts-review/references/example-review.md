# Example review: Session archive change

Illustrative output shape; findings below are hypothetical mutations of the current starter, not findings against its captured source.

**Verdict**: REQUIRES CHANGES
**Reviewers**: typescript-reviewer, background-jobs-specialist, testing-reviewer

## Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| Duplicate delivery preserves one archive | MET | Existing job-identity publication path, test required for changed branch |
| Stale owner cannot acknowledge | UNMET | Hypothetical diff removes ownership token from complete |
| Shutdown waits for active storage work | PARTIAL | Proposed timeout test absent |
| Native UI works | NOT AVAILABLE | No native UI scope or device test supplied |

## Findings

### BLOCKER: stale job acknowledgement

**Location**: changed complete call in apps/worker/src/runner.ts (cite actual line when reviewing).
**Trigger**: a lease expires and another worker reclaims the job before the first acknowledges.
**Impact**: acknowledgement without the current ownership token can mark another attempt complete.
**Evidence**: compare changed call with JobOwnership in packages/db/src/repository.ts and job-lease contract.
**Remedy**: retain token/deadline fencing; add stale-owner regression coverage.

## Verification

Record exact command/exit/log; never invent a green result. Preserve unexecuted SQL coverage separately from passing memory tests.

## Next steps

Use ts-triage or ts-plan with this review path for coordinated fixes. Use ts-work only with an existing accepted plan. A read-only review does not itself apply the change.

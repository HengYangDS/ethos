## Why

GitHub dev ETHOS CI run `30172606031` evaluated exact commit
`b2e474590234622fde1631a4ddb514fef6386a9f`. Its repository-proof job executed
one full HEAD-bound proof as intended by the predecessor change. That proof
passed all 21 gates and emitted evidence digest
`926921043d7364cbbdbfc6c6f54b9c94fc80e77aaa98c30c3521c920520617f2`, but the
job still failed.

The retained readiness artifacts explain the deterministic mismatch:
`run-head-bound-proof.sh` ran `ethos report --json` before
`ethos prove --execute`. In a clean hosted checkout, the report therefore saw no
coverage artifact and no executed proof. It recorded
`coverage_artifact_missing:build/evidence/quality/tests/coverage/coverage.xml`
and `proof_not_proven`; the later proof then generated both artifacts
successfully, but the compact receipt combined that successful proof with the
stale pre-proof report and returned non-zero.

Before the predecessor removed GitHub's redundant standalone full-test step,
that earlier step incidentally created coverage before the report ran. The
ordering defect was therefore masked by the duplication. The predecessor's
single-execution decision remains valid; the receipt pipeline must stop relying
on a removed accidental producer.

## What Changes

- Execute the HEAD-bound proof before the readiness report in
  `tools/ci/scripts/run-head-bound-proof.sh`.
- Keep audit first, execute proof exactly once, then let report observe the same
  execution's coverage and proof state before combining the receipt.
- Add a behavioral regression test that runs the real owner script against a
  controlled command adapter and fails when report precedes proof.
- Add a quality requirement, bounded Claim/Chronicle evidence, and refreshed
  generic parity evidence when admitted.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: subject=github-proof-report-after-execution; reuse=extend;
  change=modify; facet:lifecycle=validation;
  facet:surface=ci,test,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence.

## Out Of Scope

- Restoring the redundant direct GitHub test step.
- Changing the proof graph, gate registry, worker count, timeout values, coverage
  policy, or automatic retry behavior.
- Reclassifying the failed hosted run as passing or rerunning it unchanged.
- Changing, probing, pushing, fetching, or otherwise observing GitLab while the
  workstation is outside the intranet.
- Acting on foreign Work Lanes or introducing host-global scheduling authority.

## Impact

One reusable hosted-proof owner script, one provider architecture test, one
quality OpenSpec requirement, bounded Claim/Chronicle evidence, and generic
parity evidence. No GitHub workflow shape, product runtime, dependency, GitLab
projection, proof graph, timeout, worker, or retry-policy change.

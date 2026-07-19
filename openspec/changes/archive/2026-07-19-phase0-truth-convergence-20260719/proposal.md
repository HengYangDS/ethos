## Why

ETHOS currently permits three contradictory local-readiness projections. An
empty coverage writer-lock directory suppresses the missing-artifact hard gap
even though no owner process exists and the test runner cannot reclaim the
lock. Bounded `status` and `orient` readers report exact zero dirty/closeout
counts even though they deliberately did not inspect those facts. Finally,
`report` and `publish` can remain locally green while a current product hard
quality check such as generated-artifact topology is blocked.

These are truth-boundary failures: unknown or invalid local state is being
presented as a completed fact. Phase 0 must restore one fail-closed local
readiness decision before any broader productization work proceeds.

## What Changes

- Validate coverage writer ownership from the owner PID and process-start
  fingerprint rather than directory presence.
- Keep a genuinely active writer distinguishable as `in_progress`, but block
  hard-quality and publication readiness until the artifact exists.
- Let the owner test script reclaim dead or persistently invalid writer locks
  without preempting a live owner.
- Represent deferred foreign-lane dirty, overlap, and closeout aggregates as
  unknown/deferred rather than integer zero in bounded readers.
- Make product report, enterprise readiness, proof planning, and publish
  readiness consume the same current hard-quality blocker set, including
  generated-artifact topology.
- Prove, archive, land, and perform accepted-root local closeout without remote
  push or hosted-CI claims.

## Capabilities

### Modified Capabilities

- `quality`: subject=phase0-local-quality-truth; reuse=extend; change=modify; facet:lifecycle=validation,runtime,release; facet:surface=cli,test,ci,evidence; facet:authority=source,test,openspec,evidence
- `repository-governance`: subject=phase0-reader-and-publication-truth; reuse=extend; change=modify; facet:lifecycle=validation,runtime,release; facet:surface=cli,schema,test,openspec; facet:authority=source,test,schema,openspec

## Impact

- Coverage policy reader and Python test owner script.
- Workspace-status coordination schema and bounded status/orient projections.
- Product hard-quality scorecard and publish-readiness admission.
- Focused tests, OpenSpec deltas, claim, chronicle, and parity evidence.

## Out Of Scope

- Source-budget debt settlement.
- Foreign Work Lane cleanup, retirement, reset, stash, or deletion.
- Profile/adoption redesign, distribution publication, or public package release.
- Remote push, hosted CI success, or independent-verification claims.

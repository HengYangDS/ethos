## Why

ETHOS currently treats OpenSpec creation, official archive, canonical-spec
projection, Git commit finalization, and Lease advancement as separate checks.
When one effect partially completes, later readers disagree: a completed
archive can be reported as an uncovered active mutation, and a signed Change
start can leave a current Git commit with the Lease still bound to its archived
predecessor. This is the same failure class seen in adopted repositories after
official OpenSpec archive and in ETHOS's own interrupted lifecycle commit.

## What Changes

- **BREAKING** Make one verified OpenSpec lifecycle effect the authority for its
  complete finalization boundary: official child result, archived or active
  carrier, canonical projections, exact index/overlay, Git old/new objects,
  Lease generation, and terminal Attestation.
- Rename and extend the existing archive-effect requirement so archive
  finalization and recoverable Change-start finalization share one contract.
- Make status, plan, prove, land, prewrite, and hooks consume the same effect
  scope and finalization facts instead of independently requiring an active
  Change after official archive.
- Recognize an already-created signed lifecycle commit with later ancestry and
  recover its exact successor Lease through the existing public start/recovery
  command; never create a second commit or infer authority from path names.
- Classify missing Lease, expired same-holder Lease, different-holder Lease,
  and ownerless finalization separately, with one exact next command for each.
- Record true mutation, compensation, and residue states in immutable receipts;
  a zero-effect failure SHALL NOT report cleanup failure.
- Add focused regressions for official OpenSpec 1.9 archive finalization,
  multi-commit partial start recovery, missing Lease, stale authority, and
  hook lock re-entry.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: replace archive-only path attribution with one
  lifecycle-effect finalization authority and exact recovery contract.

## Impact

- OpenSpec lifecycle admission and public status/plan/prove/land projections
- Work Lane Lease and Attestation finalization
- prewrite and Git transaction hook admission
- archive and start-change recovery receipts
- unit and adopted-repository lifecycle regressions

Out of scope: AIGW/Proxy source changes, runtime distribution, release-tag
publication, and new OpenSpec schemas. OpenSpec 1.9 remains the sole official
specification workflow and archive engine.

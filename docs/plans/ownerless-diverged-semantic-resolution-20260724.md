---
subject: ethos:ownerless-diverged-semantic-resolution-20260724
role: plan
state: active
relations:
  authority: evidence/claims/all-lanes-authorized-closeout-20260718.toml
  evidence: evidence/chronicle/ownerless-diverged-semantic-resolution-20260724/2026-07-24.md
---

# Ownerless Diverged Work Lane Semantic Resolution — 2026-07-24

Status: active local resolution carrier. The first 24-lane family is complete,
the 12-lane resolution/retirement/history family is decision-ready, and the
remaining 35 lanes stay pending until their family decisions are accepted.

Purpose: provide exact, reviewable, family-level disposition evidence for
missing-lease Work Lanes while preserving dirty recovery bytes and protecting
every live lease.

## Objective

Resolve only Work Lanes that currently have no live Lane Lease. Preserve every
recoverable dirty byte, absorb useful semantics into accepted truth, explicitly
reject obsolete alternatives, retire exact superseded carriers one at a time,
and leave every currently leased lane untouched.

## Current Boundary

At accepted `dev`, `main`, and `candidate/dev` HEAD `32f66ffedc7bc3515b99a8f8aeb681d769766c3c`, the accepted
checkout is clean. The reader inventory contains 54 foreign Work Lanes: seven
have a live lease and are protected; 47 have `lease_state=missing`, all diverge
from accepted, 33 are clean, and 14 are dirty. No new ownerless branch appeared
after the first family closeout.

The initial exact cohort contained 71 ownerless lanes. Twenty-four OpenSpec
identity-normalization lanes have now completed verified `preserve-retire`.
Twelve resolution, retirement, and history lanes are decision-ready. The other
35 remain pending.

A live lease is a protection boundary even when its Claim binding is missing.
The controller excludes all seven leased lanes, including its own carrier.

## Decision Method

1. Reobserve branch, path, HEAD, status bytes, lease, Claim binding, and relation
   to accepted immediately before every decision and effect.
2. Collapse strict Git ancestry into lineages so predecessors are not treated as
   independent proposals when a later tip already contains them.
3. Compare each maximal tip with current accepted source, tests, specs, Claims,
   Chronicles, and accepted evolution. Blob inequality alone never proves
   missing semantics.
4. Classify useful semantics as already absorbed, requiring focused replay,
   explicitly rejected, or blocked. Record basis, rejected options, evidence,
   owner boundary, and review trigger.
5. Use exact `preserve-retire` for a diverged target only after accepted semantic
   absorption. The immutable repository bundle preserves provenance without
   retaining a live Work Lane. Dirty targets additionally require package-v2
   index, tracked, and untracked reconstruction checks.
6. Use unbundled `retire` only when repository-family admission proves a clean
   accepted ancestor.
7. Apply one lane at a time and prove path, ref, registration, lease, package,
   receipt, and resolution-inventory postconditions before continuing.

## Completed Family: OpenSpec Identity Normalization

All 24 members were reobserved at the recorded heads and resolved individually.
Every branch, path, worktree registration, and status row is absent. Every
repository bundle and receipt verifies. The dirty V26 package reconstructs all
seven logical files exactly; macOS AppleDouble entries were bounded and
classified as metadata sidecars rather than semantic files.

Accepted `identifiers.py` remains the single live grammar owner. The alternate
historical `identity.py` spine is rejected.

## Decision-Ready Family: Resolution, Retirement, and History

The exact 12 members are:

- `work/history-residue-closeout-20260719`
- `work/history-residue-closeout-successor-20260719`
- `work/history-residue-closeout-successor-v2-20260719`
- `work/lane-resolution-completion-integrity-20260719`
- `work/lane-resolution-completion-integrity-successor-20260719`
- `work/lane-resolution-completion-integrity-successor-v2-20260719`
- `work/lane-resolution-completion-integrity-successor-v3-20260720`
- `work/ownerless-skill-resolution-retention-repair-20260720`
- `work/unbound-retirement-arg005-carrier-20260720`
- `work/20260719-worktree-partial-retirement-recovery`
- `work/worktree-retirement-remainder-successor-20260719`
- `work/worktree-retirement-remainder-successor-v2-20260720`

Current accepted truth contains the later history-residue archives, stable
resolution-record ownership, pre-effect receipt reservation, exact identity and
accepted-CAS checks, zero-effect retry recovery, closeout fencing, package-v2
staged-index preservation, and current ownerless retirement effects. A focused
current-head suite passes 440 tests with warnings treated as errors. Resolution
inventory is ready with 142 packages, 40 receipts, and zero inflight or partial
records.

The live invariants are absorbed. Obsolete mixed implementations, incomplete
remainder checkpoints, and dirty completion-integrity variants are rejected.
The ARG005 carrier is explicitly historical one-off authority and must not be
reused. All 12 heads diverge from accepted, so their terminal disposition is
`preserve-retire`, not an unbundled claim of integration. The three dirty lanes
require exact package-v2 reconstruction.

## Remaining Ordered Families

1. OpenSpec lifecycle, adoption, and declarative state: 7 lanes.
2. Quality, lint, and exception elimination: 9 lanes.
3. Publication, remote, hosted CI, and npm supply: 8 lanes.
4. Candidate, ledger, delegation, documentation, evidence, and remaining
   governance: 11 lanes.

## Completion Criteria

- all 71 initial ownerless observations have a family, semantic basis, accepted
  Chronicle decision, and terminal local disposition;
- every dirty target has a verified reconstructable v2 recovery package;
- every retired target is absent as path, ref, worktree registration, and lease;
- every protected leased lane remains outside this controller;
- resolution inventory has no inflight, partial, conflicting, or unverified
  record;
- housekeeping, repository-family audit, status, report, parity, executed proof,
  candidate land, and accepted closeout are rerun on the final stable HEAD; and
- the external evidence record is verified and indexed.

Remote push, hosted-provider success, release/tag publication, and distribution
remain separate and are not authorized by this plan.

## See Also

See also:

- [Authorized Work Lane Cohort Closeout](all-lanes-authorized-closeout-20260718.md)
- [All Work Lanes Convergence](all-work-lanes-convergence-implementation-plan-20260716.md)
- [Ownerless Closeout Admission](ownerless-closeout-admission-implementation-plan-20260722.md)
- [Mutation Rules](../../rules/mutation.md)
- [Evidence Rules](../../rules/evidence.md)

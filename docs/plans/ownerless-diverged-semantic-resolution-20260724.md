---
subject: ethos:ownerless-diverged-semantic-resolution-20260724
role: plan
state: active
relations:
  authority: evidence/claims/all-lanes-authorized-closeout-20260718.toml
  evidence: evidence/chronicle/ownerless-diverged-semantic-resolution-20260724/2026-07-24.md
---

# Ownerless Diverged Work Lane Semantic Resolution — 2026-07-24

Status: active local resolution carrier. The OpenSpec identity-normalization
family is decision-ready; all other ownerless families remain pending until
their own analysis is recorded and accepted.

Purpose: provide exact, reviewable, family-level disposition evidence for
missing-lease Work Lanes while preserving dirty recovery bytes and protecting
every live lease.

## Objective

Resolve only Work Lanes that currently have no live Lane Lease. Preserve every
recoverable dirty byte, absorb useful semantics into accepted truth, explicitly
reject obsolete alternatives, retire exact superseded carriers one at a time,
and leave every currently leased lane untouched.

## Frozen Current Boundary

At accepted `dev`, `main`, and `candidate/dev` HEAD
`ae759420a2aab97352955a0323666d18e7772d9e`, the exact reader inventory contains
79 foreign Work Lanes. Eight have a live lease, including this controller's
carrier, and are protected. Seventy-one
have `lease_state=missing`; all 71 diverge from accepted, 56 are clean, and 15
are dirty. Their commit ancestry collapses to 47 maximal tips: one 24-lane
OpenSpec identity-normalization chain, one two-lane completion-integrity chain,
and 45 singleton components.

A live lease is a protection boundary even when its Claim binding is missing.
The controller therefore excludes all eight leased lanes, including its own
carrier, `work/20260723-ownerless-closeout-compression`, and
`work/20260724-budget-contract-v2-snapshot-replay-shadow-successor`.

## Decision Method

1. Reobserve branch, path, HEAD, status bytes, lease, Claim binding, and relation
   to accepted immediately before every decision and every effect.
2. Collapse strict Git ancestry into lineages so an old clean predecessor is not
   analyzed as an independent product proposal when a later tip already contains it.
3. Compare the maximal tip with current accepted source, tests, specs, Claims,
   Chronicles, and accepted evolution. Final blob inequality alone never proves
   missing semantics.
4. Classify useful semantics as already absorbed, requiring focused replay,
   explicitly rejected, or blocked. Record context, rejected options, evidence,
   owner boundary, and review trigger.
5. For any diverged target whose useful semantics are already absorbed, use exact
   `preserve-retire`: its immutable repository bundle keeps provenance without
   keeping the Work Lane live. Dirty targets additionally require preservation-
   package v2 index, tracked, and untracked reconstruction checks. Never use
   stash or manual cleanup.
6. Use unbundled `retire` only when repository-family admission can prove a clean
   accepted-ancestor relation. All 24 members of the first lineage are diverged,
   so the native accepted-ancestor route is intentionally not bypassed; bounded
   `preserve-retire` is the safe terminal effect after semantic absorption.
7. Apply one lane at a time. After each effect, prove path, ref, registration,
   lease, package, receipt, and resolution inventory postconditions before the
   next lane.

## Ordered Families

1. OpenSpec identity-normalization lineage (24 lanes).
2. Lane-resolution, retirement, and history-residue lineages.
3. OpenSpec lifecycle, adoption, and declarative-state lineages.
4. Quality, lint, and exception-elimination lineages.
5. Publication, remote, hosted-CI, and npm-supply lineages.
6. Candidate, ledger, delegation, documentation, evidence, and remaining
   governance lineages.

The order deliberately resolves the largest ancestry chain first, then reuses
current accepted contracts to reduce duplicated analysis while never treating
age or branch naming as retirement evidence.

## First Family Decision

The 24-lane OpenSpec identity-normalization lineage is superseded by accepted
`openspec-identity-normalization-current`. After the bounded GitHub pytest-timeout
change, this decision carrier itself advanced accepted from `f1e2481a` to
`ae759420`; fresh observation proves the same 71 ownerless targets and exact
24-member lineage remain. Current accepted lifecycle and Claims checks are clean
across 237 Claims, strict OpenSpec validation passes 9/9, and a 102-test focused
OpenSpec, identity, Claim, schema, and invalid-state suite passes with warnings
treated as errors. The V26 tip's own untracked Claim, Chronicle, proposal, design,
and tasks say that candidate drift ended its integration eligibility and forbid
refresh, cherry-pick, manual replay, proof, or land.

All 24 heads are diverged from accepted. Repository-family ownerless `retire` is
correctly limited to clean accepted ancestors, so treating the 23 clean historical
heads as integrated would be false. The exact terminal disposition is therefore
`preserve-retire` for every member: each lane is removed, while an immutable
repository bundle preserves provenance; V26 additionally preserves and verifies
its seven untracked stale-boundary records through package v2. This is recovery
retention after semantic absorption, not promotion or indefinite lane preservation.
The alternate historical `identity.py` spine remains explicitly rejected because
accepted `identifiers.py` is authoritative and retaining both would recreate
duplicate identity grammar ownership.

## Completion Criteria

- every one of the 71 exact ownerless observations has a family, semantic basis,
  accepted Chronicle decision, and terminal local disposition;
- every dirty target has a verified reconstructable v2 recovery package;
- every retired target is absent as path, ref, worktree registration, and lease;
- every protected leased lane remains unchanged;
- resolution inventory has no inflight, partial, conflicting, or unverified record;
- housekeeping, repository-family audit, status, report, parity, executed proof,
  candidate land, and accepted closeout are rerun on the final stable HEAD;
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

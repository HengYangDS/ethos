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
`f1e2481ad0e77247953c81b6b69dfe2de44c2205`, the exact reader inventory contains
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
5. For dirty targets, use `preserve-retire` with preservation-package v2,
   verify manifest, tracked patch, index patch, untracked archive, receipt, and
   reconstruction before accepting deletion. Never use stash or manual cleanup.
6. For clean targets, use `retire` only after the accepted Chronicle authorizes
   that exact HEAD. Run repository-family closeout check even when divergence is
   expected to block its normal integrated-lane path; retain that result as a
   boundary observation before native exceptional resolution.
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
`openspec-identity-normalization-current`. The accepted train advanced from `fe94c0268`
to `f1e2481a` through the bounded GitHub pytest-timeout resilience change and
its parity receipts; the 71-target ownerless set and this family judgment did
not change. Current accepted lifecycle and Claims
checks are clean across 236 Claims, strict OpenSpec validation passes 9/9, and
the focused identity suite passes 85 tests. The V26 tip's own untracked Claim, Chronicle, proposal,
design, and tasks say that candidate drift ended its integration eligibility and
forbid refresh, cherry-pick, manual replay, proof, or land.

Therefore the 23 clean predecessors are selected for exact `retire`, and the
dirty V26 tip is selected for v2 `preserve-retire`. Its seven untracked stale-
boundary records are recovery evidence, not product semantics to discard or
silently promote. The alternate historical `identity.py` spine is explicitly
rejected because accepted `identifiers.py` is authoritative and retaining both
would recreate duplicate identity grammar ownership.

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

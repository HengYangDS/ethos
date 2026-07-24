---
subject: ethos:ownerless-diverged-semantic-resolution-20260724
role: plan
state: active
relations:
  authority: evidence/claims/all-lanes-authorized-closeout-20260718.toml
  evidence: evidence/chronicle/ownerless-diverged-semantic-resolution-20260724/2026-07-24.md
---

# Ownerless Diverged Work Lane Semantic Resolution — 2026-07-24

Status: active local execution carrier. Thirty-six lanes are complete and the
remaining 35 are decision-ready after current-head semantic analysis.

Purpose: resolve the initial 71 missing-lease Work Lanes without losing dirty
bytes, preserving obsolete implementations as live lanes, or touching any valid
owner's lane.

## Current Boundary

Accepted dev, main, candidate/dev, and this controller started this decision at
738a75aeca0e9264462f0d6abf04bf15722d9329. The accepted and candidate checkouts were clean. The exact
reader observation contained 43 foreign Work Lanes: 35 had
lease_state=missing and 11 of those were dirty; eight had live leases and are
protected.

Ownerlessness is never inferred from age, process absence, or a missing Claim.
Every effect must reobserve the same branch, HEAD, path, dirty bytes, and
lease_state=missing.

## Completed Families

- OpenSpec identity-normalization lineage: 24 verified preserve-retire effects.
- Resolution, retirement, and history lineage: 12 verified preserve-retire effects.

After the second family the resolution inventory was ready with 154 packages,
52 receipts, and no inflight or partial record.

## Decision-Ready Families

### OpenSpec Lifecycle, Adoption, and Declarative State

- work/adopter-openspec-schema-compatibility-20260715
- work/archived-openspec-identifier-normalization-current-absorption-v22-20260720
- work/archived-openspec-identifier-normalization-successor-v21-20260720
- work/declarative-lifecycle-matrix-20260720
- work/lifecycle-transition-fail-closed-20260719
- work/lifecycle-transition-review-repair-successor-20260720
- work/openspec-new-capability-lifecycle-20260715

Current official OpenSpec lifecycle, identity, profile, archive, declarative
lease, handoff, resolution, and fail-closed transition owners absorb these
semantics. The dirty review-repair successor is preserved but superseded.

### Quality, Lint, and Exception Elimination

- work/lint-small-tests-20260719
- work/quality-exception-elimination-foundation-20260715
- work/quality-zero-exceptions-20260718
- work/quality-zero-exceptions-successor-20260719
- work/ruff-discovery-adapter-20260720
- work/e501-hosted-evidence-core-20260719
- work/perf401-product-core-20260719
- work/quality-a002-exemption-elimination-20260720
- work/quality-law-20260712

The accepted exact Ruff ratchet remains authoritative. E501 hosted and A002
affected scopes are at zero, but PERF401 remains 32 corpus-wide and 27 in
product scope. Wholesale zero-exception snapshots and the staged 80-path
ratchet deletion are rejected; their bytes remain recoverable.

### Publication, Remote, Hosted CI, and npm Supply

- work/brand-public-surface-20260722
- work/dual-remote-publication-equivalence-20260718
- work/dual-remote-publication-topology-20260715
- work/github-hosted-ci-reconciliation-20260717
- work/npm-supply-governance-20260716
- work/release-mirror-policy-20260712
- work/remote-mirror-reconciliation-20260717
- work/remote-reconciliation-resume-r7-20260718

Equal GitLab and GitHub topology, local, remote, and hosted evidence separation,
atomic accepted_ff closeout, and current release supply owners absorb the live
contracts. Remote push and hosted success remain unclaimed. The standalone
Linux npm installer is rejected as a second supply authority.

work/brand-public-surface-20260722 is the exception to pure supersession: its
seven presentation assets are replayed byte-exact into this carrier, and its
README, documentation, format, and source-budget semantics are adapted to
current owners before the lane is preserved and retired.

### Candidate, Ledger, Delegation, Documentation, Evidence, and Governance

- work/all-lanes-convergence-implementation-20260716
- work/budget-contract-v2-native-measurement-20260719
- work/ddwg-accepted-state-binding-20260720
- work/docs-semantic-navigation-coverage-20260715
- work/expert-review-remediation-20260716
- work/feedback-completion-20260720
- work/principal-delegation-foundation-20260712
- work/skill-script-closeout-integrity-repair-20260720
- work/candidate-generation-lease-20260714
- work/lane-ledger-integrity-20260712
- work/runtime-evidence-isolation-20260713

Current budget v4, resolution state, proof carry, profile normalization,
candidate lifecycle, ledger fencing, runtime evidence, and minimal docs
topology absorb the durable invariants. A first-class Principal or Agent
registry is explicitly rejected, as is the repetitive 112-path
document-backlink graph.

## Effect Protocol

1. Reobserve one exact family member.
2. Stop if it has gained a lease, changed HEAD, or changed dirty bytes.
3. Record an accepted preserve-retire decision.
4. Confirm ordinary worktree closeout does not falsely admit the diverged lane.
5. Create and verify one immutable repository bundle and package-v2 payload.
6. Verify tracked, index, untracked, receipt, ref, path, registration, inventory,
   accepted-root, and protected-owner postconditions before continuing.

## Completion Criteria

- all 71 initial lanes are either completed or have an accepted exact decision;
- all 11 remaining dirty targets receive verified reconstructable package-v2
  preservation;
- all retired targets are absent as path, ref, worktree registration, and lease;
- all eight currently leased lanes remain outside this controller;
- resolution inventory remains free of inflight, partial, conflicting, or
  unverified records;
- safe housekeeping removes only proven tool residue or prunable registrations;
- final status, report, parity, quality, proof, candidate land, accepted
  closeout, repository-family audit, and record verification pass; and
- the controller retires only after its accepted completion record is landed.

Remote mutation, hosted-provider success, release or tag publication, and
distribution publication are excluded.

## See Also

See also:

- [Authorized Work Lane Cohort Closeout](all-lanes-authorized-closeout-20260718.md)
- [All Work Lanes Convergence](all-work-lanes-convergence-implementation-plan-20260716.md)
- [Ownerless Closeout Admission](ownerless-closeout-admission-implementation-plan-20260722.md)
- [Mutation Rules](../../rules/mutation.md)
- [Evidence Rules](../../rules/evidence.md)

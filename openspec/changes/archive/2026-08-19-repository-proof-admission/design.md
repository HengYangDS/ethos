## Context

An exact Git commit can legitimately accumulate more than one proof. A Work
Lane proof is bound to its Change Commitment and Lease generation; a later
repository proof is bound to the repository Commitment. The generic proof reader
correctly reports these bindings as different, but lifecycle code used that
generic ambiguity as mutation admission. Readiness skipped that check while
apply performed it, producing a pass/block split for the same closeout request.

The product contract already defines a query-specific authority chain. The
repair therefore narrows selection instead of adding another proof type or
compatibility branch.

## Goals / Non-Goals

**Goals:** one query for repository role transitions; exact repository, HEAD,
tree and policy binding; deterministic repository-proof preference; bounded
archive fallback after lane retirement; conflict detection inside the selected
authority; and dry-run/apply parity.

**Non-Goals:** changing proof generation, weakening generic proof ambiguity,
reviving retired Lease generations, deleting Attestations, adding a transition
command, or modifying AIGW/Proxy.

## Decisions

1. `repository_transition_proof` is the sole selector for Git role movement.
   Generic `proof_attestation` remains the inspection query and may report
   cross-authority ambiguity.
2. Candidate proof candidates are first filtered by exact subject and repository
   identity, then validated against exact tree, proof artifacts, proof policy,
   scope, plane and context.
3. An exact repository-Commitment proof wins. An archive-authorized proof is a
   fallback only when no repository proof exists and its archive authority
   covers the proof scope.
4. Lease-generation freshness applies while a Work Lane is current. An
   archive-authorized proof does not become stale merely because its retired
   generation is absent; repository, HEAD, tree, policy and archive scope remain
   mandatory.
5. Conflict detection groups proofs by applicable Commitment authority. Two
   proofs from distinct authorities are not contradictory merely because both
   are retained; differing proofs inside the selected authority fail closed.
6. Readiness and apply call the same query. Apply may add authorization and CAS
   checks, but not a different proof predicate.

## Alternatives Rejected

- Delete older Attestations: destroys immutable evidence and makes correctness
  depend on garbage collection.
- Accept the newest proof: time ordering does not establish authority.
- Require repository Commitment digest only: rejects legitimate post-archive
  proof before a repository reproof exists.
- Ignore all conflicts: permits contradictory applicable proofs.
- Preserve separate selectors per command: recreates the parity defect.

## Proof Strategy

Focused tests construct one exact HEAD with repository and archived proofs,
retire the Work Lane generation, and verify deterministic selection, repository
isolation, and conflict failure. A public closeout regression executes readiness
and apply against that same proof set. Existing control-replacement and publish
tests prove reuse rather than rebuilding selector semantics.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| Repository-transition query selects applicable authority | 2.1 | `tests/unit/kernel/test_proof_plan_binding.py` |
| Lifecycle consumers use one selector | 2.2 | focused consumer tests and repository-wide reference search |
| Closeout readiness and apply agree | 2.3 | `tests/unit/cli/test_contracts_closeout.py` |
| Applicable conflicts fail closed | 2.1 | proof conflict matrix |

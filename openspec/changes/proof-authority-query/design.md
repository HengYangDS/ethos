# Design

## Problem

The generic proof resolver first selects by HEAD and repository-shaped payload,
then validates every selected proof against live Lease state. This reverses the
authority relation: an obsolete Work Lane generation is treated as applicable
to `candidate.accept`, so its expected Lease state can veto a current repository
proof. Filtering only after evaluation cannot fix the model because stale
non-applicable evidence has already become a blocking input.

## Decision

Introduce one frozen transient `ProofQuery` value. It names the exact subject
HEAD, repository Commitment digest, operation, proof floor, scope, plane, and
boundary required by a consumer. It is a query only: it is not persisted and
cannot mint authority.

Proof admission proceeds in this order:

1. load current Attestations from the sole Git set;
2. select proof predicate and exact HEAD;
3. validate immutable Attestation and artifact integrity;
4. retain only proofs whose statement is applicable to the query, including
   exact Commitment authority and operation boundary;
5. validate mandatory dependencies declared by the retained proof;
6. select the required proof floor; and
7. reject different bindings or assertions only among proofs applicable to the
   same query.

`candidate.accept` constructs its query from the candidate HEAD repository
Commitment and explicit operation. Its repository proof therefore remains valid
after a historical Work Lane Lease disappears. Generic callers retain their
existing repository query semantics; Work Lane operations continue to validate
the exact live Lease generation declared by their applicable proof.

## Fail-closed boundaries

- Wrong HEAD, repository Commitment, scope, plane, boundary, or proof floor is
  not applicable and cannot authorize the operation.
- Absence of an applicable proof reports the most specific query mismatch.
- Two applicable proofs with different exact bindings remain `stale_binding`.
- Two applicable proofs with contradictory assertions remain `contradiction`.
- Query construction, filtering, and selection never supersede, delete, or
  mutate historical Attestations.

## Verification

Focused tests materialize a historical Work Lane proof and a current repository
proof at one HEAD, retire the lane generation, and prove `candidate.accept`
selects only the current repository authority. Negative cases cover wrong HEAD,
wrong repository Commitment, wrong operation, stale applicable Lease, and true
same-query binding or assertion conflicts. Public closeout tests prove dry-run
and apply consume the same selected proof.

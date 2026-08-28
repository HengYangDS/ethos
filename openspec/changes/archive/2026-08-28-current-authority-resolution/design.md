## Context

A current owned Work Lane already has the sufficient mutation coordinates:
branch/ref HEAD and tree, invocation actor, Lease ID and epoch, and the exact
Commitment carrier bytes and semantic digest bound by that Lease. Historical
start, rebind, and archive Attestations explain how those coordinates arose but
cannot mint present permission.

Three paths currently overlap:

1. prewrite checks the fresh Lease and exact Lease-bound Commitment;
2. workspace stage gates infer authoring permission from closeout gaps;
3. generation observation may turn missing historical effect Attestations into
   change_generation_authority_missing.

## Decision

Promote the existing admission Lease-binding module into the single current
authority resolver. It returns a closed projection containing verdict, one
reason, exact Lease/Commitment coordinates, and the loaded Commitment when
valid. Prewrite consumes it directly. Status and plan consume the same
projection rather than reconstructing permission from closeout or historical
generation evidence.

Generation observation remains responsible for selecting and attributing the
current lane delta. Missing transition evidence may reduce provenance detail,
but it does not invalidate an otherwise exact current Lease binding.

## Deletion

- Delete change_generation_authority_missing as a current authoring blocker.
- Delete workspace authoring inference from closeout gaps.
- Delete duplicate Commitment loading after a successful current-authority
  resolution.
- Retain effect Attestation validation only for provenance and effect-time
  verification.

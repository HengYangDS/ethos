# Design

## Context

See the [proposal](proposal.md). A proof's plan facts record the Lease generation it ran under
(`lane_ref`, `generation`, `holder_ref`, `expires_at`). The lane-level proof query refuses a proof
whose generation is not the lane's current one (`proof_lease_generation_stale`). A repository
transition, such as the candidate update of `land` or the accepted-ref hook, skips that check,
because the lane may already be retired when the transition runs. The repository-governance
requirement "Native accepted-ref admission agrees with transition proof" makes proofs of one HEAD
with different verifiers contradictory.

## Goals / Non-Goals

Goals: a handed-off lane lands on its new holder's proof without any manual release.

Non-Goals:

- Changing the contradiction rule for proofs of one generation.
- Applying the current-Lease check to repository transitions, which may run after a lane retires.

## Decisions

1. Supersession is read from the proofs themselves, not from the current Lease: among valid
   candidates, a proof whose recorded generation for a lane is lower than another candidate's for
   the same lane drops out. A proof that records no lane is unaffected, and a lone proof is never
   dropped.
2. The filter runs on the valid candidates, before the binding and contradiction comparisons, so a
   malformed or tampered proof still blocks the set, as the integrity rule requires.

## Risks / Trade-offs

- An older holder's proof of the same HEAD can no longer veto a newer holder's. That is the intent
  of a handoff, and both proofs stay in the Attestation set as history.

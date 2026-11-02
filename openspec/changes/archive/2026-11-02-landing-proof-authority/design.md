# Design

## Context

See [proposal.md](proposal.md). The candidate effect of `ethos land` binds one Commitment as its
authority, and the comment above that lookup states the intent: "the encoding of the exact source
that the admitted proof carries" (`src/ethos/adapters/mutation/landing.py`). The lookup calls
`admissible_openspec_commitments` without a Change, which selects the active Change or the archive
nearest the head, so it finds the proof's encoding only when the proof carries that default.

## Goals / Non-Goals

**Goals:**

- A proof that proof admission accepts at the head is the authority that landing binds.

**Non-Goals:**

- Choosing between several valid proofs of different Changes at one head. They remain
  `stale_binding` until an explicit selection names one, as "Exact proof query selects intent
  without weakening evidence" requires.
- Refusing at proof time a Change other than the default. Once landing honors the carried Change,
  such a proof is landable.

## Decisions

- **Read the Change from the proof's own plan.** The admitted proof carries its full Commitment in
  its TransitionPlan. Landing compiles that Change's admissible encodings at the head and keeps the
  one whose digest the proof names. A proof without a carried Commitment keeps today's lookup.
- **Keep the refusal.** If no admissible encoding matches, landing still raises
  `proof_attestation_authority_binding_mismatch` and the candidate branch does not move.

## Risks / Trade-offs

- [A proof could carry a Change from outside the lane] → Landing adds no weaker path: the proof is
  already admitted only when its carried Change matches its exact source at the head and its archive
  effect lies within the lane's changed paths.

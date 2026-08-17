# Design

## Problem

The generic resolver validates every same-HEAD proof against live Lease state,
so a historical Work Lane generation can veto the repository proof required by
candidate acceptance.

## Decision

The existing resolver accepts one optional repository Commitment and filters
other Commitments before Lease or conflict evaluation. Candidate acceptance
supplies it from candidate HEAD. Generic semantics remain unchanged; no query
entity, ledger, store, or wrapper is added.

## Fail-closed boundaries

- Wrong HEAD or repository Commitment cannot authorize candidate acceptance.
- Same-authority binding or assertion conflicts remain `stale_binding` or
  `contradiction`.
- Selection never mutates historical Attestations.

## Verification

A focused test proves same-HEAD generic ambiguity, exact repository selection,
wrong-Commitment rejection, and same-authority conflict closure.

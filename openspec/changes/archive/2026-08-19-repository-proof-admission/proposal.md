## Why

Repository closeout currently has two proof interpretations. Readiness accepts
any valid proof on the candidate HEAD, while apply may reject the same HEAD when
an archived Change proof and a repository proof coexist. This makes the public
dry-run and mutation disagree and leaves candidate acceptance, publication, and
control replacement with separate selectors.

## What Changes

- Replace command-specific proof selection with one repository-transition
  query bound to the repository identity, exact HEAD and tree, current proof
  policy, and the applicable Commitment authority.
- Prefer an exact repository-Commitment proof when present; otherwise admit an
  archive-authorized proof for the same repository after its Work Lane is no
  longer current.
- Detect contradictions only within the selected authority instead of treating
  proofs from different, non-applicable authorities as one conflict set.
- Make closeout readiness and apply evaluate this same query, so a dry-run cannot
  promise a mutation that apply will reject for proof-selection reasons.
- Reuse the same query from candidate acceptance, accepted publication, and
  control-replacement admission; remove their generic-selector paths.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: repository role transitions use one query-specific
  proof admission rule across readiness and mutation.

## Impact

The change affects proof admission and its existing lifecycle consumers. It
does not add a public command, proof store, compatibility reader, or adopter
mutation, and it does not alter proof generation or generic proof inspection.

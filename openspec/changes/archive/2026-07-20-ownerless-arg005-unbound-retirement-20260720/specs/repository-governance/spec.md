## MODIFIED Requirements

### Requirement: Exceptional unbound Work Lane retirement is exact and accepted-policy-bound

ETHOS SHALL require a target-specific accepted Claim, Chronicle, and OpenSpec
carrier before `ethos lane retire unbound` retires one unbound accepted-ancestor
`work/*` ref. It SHALL bind exactly one target branch and head, re-observe the
current target, accepted relation, worktree binding, lease state, protected
refs, Claim, and Chronicle before effect, then compare-and-delete only that
ref and emit a receipt.

#### Scenario: clean ownerless parity residual is retired after absorption

- **GIVEN** `work/arg005-coverage-edges-20260719` at
  `87911a89faeb01d97a29afce1c24e0fc5ed94f2a` is unbound, clean, lease-free,
  and an accepted ancestor with no linked worktree
- **AND** current accepted history retains its historical parity semantics and
  an accepted Claim and Chronicle name the exact target
- **WHEN** an authorized native command uses break-glass and irreversible
  confirmation
- **THEN** it SHALL re-observe all target bindings before compare-and-delete
- **AND** it SHALL retire only that ref and write a receipt
- **AND** it SHALL not treat sibling history, a missing lease, or an inventory
  as authority to retire another lane.

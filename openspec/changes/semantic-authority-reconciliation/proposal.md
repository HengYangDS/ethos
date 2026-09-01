## Why

The canonical product contract and terminal plan preserve the semantic kernel,
but they still omit or under-specify several accepted terminal invariants and
delegate part of the remaining implementation order to an obsolete archived
Change. This leaves current design decisions vulnerable to loss, conflicting
interpretation, and patch-by-patch implementation.

## What Changes

- Reconcile the canonical product contract with the accepted terminal model for
  OpenSpec intent, transient Commitment compilation, derived Change relations,
  hypothesis and experiment behavior, lane and Lease recovery, local-first Git,
  proposal review, protected integration, proof selection, runtime activation,
  operational resources, documentation, and bounded break-glass.
- Replace the terminal plan's stale delegation to archived tasks with one
  dependency-ordered convergence route, explicit acceptance boundaries, and
  re-planning conditions.
- Keep implementation status honest: this Change updates design authority only
  and does not claim that the described product behavior is already implemented.

## Capabilities

### New Capabilities

None. This Change introduces no new product behavior.

### Modified Capabilities

- `repository-governance`: Require the product contract and terminal plan to
  carry the complete current semantic invariants, convergence order,
  acceptance boundaries, and exit conditions without delegating current truth
  to archived tasks or a parallel ledger.

## Impact

- Updates `docs/governance/product-design-contract.md` and
  `docs/plans/terminal-governance-product-design.md`.
- Adds only the official OpenSpec delta and planning artifacts required to
  review and verify this design-authority Change.
- Does not modify product code, tests, schemas, remotes, adopters, foreign Work
  Lanes, or repository-local runtime state.

## Routing

- Semantic meaning and invariants remain owned by the product design contract.
- Dependency order, acceptance, and exit conditions remain owned by the terminal
  governance product design.
- Physical module-layout rules remain owned by `rules/module_layout.md` and are
  referenced rather than duplicated.

## ADDED Requirements

### Requirement: Atomic Fresh Change Bootstrap

ETHOS SHALL start a new mutation-capable Work Lane from clean accepted truth
only when one explicit valid Commitment and the exact official OpenSpec Change
identity are available before the Work Lane ref is created.

#### Scenario: A fresh Change starts without a predecessor lane

- **WHEN** an operator supplies a valid Commitment for a new Change from a clean
  accepted root with a current clean candidate
- **THEN** ETHOS creates and validates the official OpenSpec carrier in a
  detached candidate-based worktree
- **AND** binds the resulting exact HEAD, tree, Commitment path, bytes, digest,
  holder, and Lease generation before creating the Work Lane ref
- **AND** ordinary tracked writes remain blocked until that transaction passes.

#### Scenario: Bootstrap intent is absent or ambiguous

- **WHEN** neither a live source Work Lane nor an explicit fresh Commitment is
  supplied, or both are supplied
- **THEN** ETHOS blocks before creating a worktree, Lease, or ref
- **AND** it does not infer intent from an archive, accepted spec, branch name,
  historical task, or conversation.

#### Scenario: A live Change continuation is requested

- **WHEN** an operator explicitly supplies a clean owned source Work Lane with
  a valid exact Lease-bound Commitment
- **THEN** ETHOS preserves the existing exact source-carrier continuation
  semantics
- **AND** the fresh bootstrap path is not also evaluated.

## MODIFIED Requirements

### Requirement: Lease-backed Lane Start
ETHOS SHALL acquire local lease records when creating Work Lanes through the
public lane command plane.

#### Scenario: Work Lane start is applied
- **WHEN** `ethos lane start <name> --commitment <path> --apply --holder-ref
  <holder-ref>` runs from a clean accepted root with a valid matching Commitment
  and succeeds
- **THEN** ETHOS creates a `work/<name>` linked worktree
- **AND** ETHOS records an active lease in ignored local state under
  `.ethos/state/state.sqlite`
- **AND** raw Git worktree creation is not treated as standard ETHOS workflow
  state because it has no ETHOS lease or claim boundary

#### Scenario: Existing Change continuation is applied
- **WHEN** `ethos lane start <name> --source-root <source-work-lane> --apply
  --holder-ref <holder-ref>` explicitly requests continuation from a clean owned
  source Work Lane
- **THEN** ETHOS copies its exact Lease-bound Commitment carrier
- **AND** it does not evaluate fresh bootstrap.

#### Scenario: Work Lane start intent is absent or ambiguous
- **WHEN** neither a Commitment nor source Work Lane is supplied, or both are
  supplied
- **THEN** ETHOS blocks before creating a worktree, Lease, or ref.

#### Scenario: Work Lane start is requested from a non-accepted or dirty root
- **WHEN** `ethos lane start <name> --apply --holder-ref <holder-ref>` runs from an
  existing `work/*` lane or a dirty accepted root
- **THEN** ETHOS blocks the request with
  `lane_start_requires_clean_accepted_root`

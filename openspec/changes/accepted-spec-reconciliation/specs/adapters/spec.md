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

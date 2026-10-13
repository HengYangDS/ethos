## MODIFIED Requirements

### Requirement: Lane retirement exposes one receipt-bound recovery route

The `ethos lane retire` command family SHALL expose one public `recover`
operation for every partial linked-lane retirement. The operation MUST accept
an immutable receipt path and digest, return the currently observed effect
progress as structured JSON, and provide exactly one copyable continuation.
It SHALL never require raw Git, direct SQLite mutation, or recreation of a
deleted checkout.

#### Scenario: Partial retirement returns its continuation

- **WHEN** a retirement effect completes but the terminal worktree, ref, and
  Lease postcondition is not reached and the receipt still applies
- **THEN** the command returns a blocking structured result with
  `state=partial_transition`, the immutable receipt identity,
  `completed_effects`, and `remaining_effects`
- **AND** `next_action` is the complete `ethos lane retire recover` command for
  that receipt.

#### Scenario: Accepted advance invalidates the receipt without losing progress

- **WHEN** the accepted head fast-forwards after a retirement receipt was
  derived
- **THEN** no remaining worktree or ref deletion runs under that receipt and
  the command reports `retirement_accepted_coordinate_drift`
- **AND** the persisted and reported progress still names every effect that
  already completed
- **AND** `next_action` is the fresh native admission for the remaining
  carriers derived from the current accepted head, which never recreates the
  deleted checkout.

#### Scenario: Any other accepted move remains carrier drift

- **WHEN** the accepted head is rewritten, rewound, or absent instead of
  fast-forwarded
- **THEN** recovery reports `retirement_operation_state_drift` and recognizes
  no progress from the receipt
- **AND** `next_action` is `ethos lane status` for the repository.

#### Scenario: Reviewed content drift requires a fresh review

- **WHEN** reviewed content no longer matches its receipt before removal
- **THEN** nothing is removed and `next_action` is a fresh content review for
  the same target instead of `recover`.

#### Scenario: Recovery is dry-run before apply

- **WHEN** `ethos lane retire recover` is invoked without `--apply`
- **THEN** it performs only receipt validation and fresh observation
- **AND** it reports the exact remaining effects and the authorized apply
  command without changing Git, worktree, Lease, or progress state.

#### Scenario: Recovery execution is structured and idempotent

- **WHEN** recovery is authorized and applied one or more times
- **THEN** every invocation returns structured JSON without a traceback
- **AND** terminal state is either newly applied or recognized from the same
  immutable request.

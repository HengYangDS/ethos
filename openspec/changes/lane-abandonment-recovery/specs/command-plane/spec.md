## ADDED Requirements

### Requirement: Lane retirement exposes one receipt-bound recovery route

The `ethos lane retire` command family SHALL expose one public `recover`
operation for every partial linked-lane retirement. The operation MUST accept
an immutable receipt path and digest, return the currently observed effect
progress as structured JSON, and provide exactly one copyable continuation.
It SHALL never require raw Git, direct SQLite mutation, or recreation of a
deleted checkout.

#### Scenario: Partial retirement returns its continuation

- **WHEN** a retirement effect completes but the terminal worktree, ref, and
  Lease postcondition is not reached
- **THEN** the command returns a blocking structured result with
  `state=partial_transition`, the immutable receipt identity,
  `completed_effects`, and `remaining_effects`
- **AND** `next_action` is the complete `ethos lane retire recover` command for
  that receipt.

#### Scenario: Recovery is dry-run before apply

- **WHEN** `ethos lane retire recover` is invoked without `--apply`
- **THEN** it performs only receipt validation and fresh observation
- **AND** it reports the exact remaining effects and the authorized apply
  command without changing Git, worktree, or Lease state.

#### Scenario: Recovery execution is structured and idempotent

- **WHEN** recovery is authorized and applied one or more times
- **THEN** every invocation returns structured JSON without a traceback
- **AND** terminal state is either newly applied or recognized from the same
  immutable request.

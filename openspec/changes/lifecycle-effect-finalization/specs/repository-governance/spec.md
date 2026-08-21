## RENAMED Requirements

- FROM: `### Requirement: Archive effect authorizes its exact transition paths`
- TO: `### Requirement: Lifecycle effect finalization authorizes exact transition paths`

## MODIFIED Requirements

### Requirement: Lifecycle effect finalization authorizes exact transition paths

ETHOS SHALL use one verified OpenSpec lifecycle-effect authority for the exact
transition paths of Change start, official archive, canonical-spec projection,
and post-archive closeout. The authority SHALL bind the repository identity,
source Commitment digest and carrier, previous HEAD/tree, exact index/overlay,
official OpenSpec result, completion artifacts, changed paths, resulting
HEAD/tree, Lease generation, and terminal effect Attestation. Status, plan,
prove, land, prewrite, and Git hooks SHALL consume this same authority rather
than infer permission from an active Change, an archive path, or a generic Lease
check. A durable partial effect SHALL be recoverable through the same public
operation by exact CAS; recovery SHALL never replay OpenSpec or create a second
product commit.

#### Scenario: Exact archive transition is congruent across readers

- **GIVEN** the official OpenSpec 1.9 archive command completed one Change and
  emitted a valid effect Attestation binding the source Commitment, resulting
  HEAD/tree, Lease generation, and exact changed paths
- **WHEN** status, plan, prove, land, prewrite, or a protected-ref hook evaluates
  the resulting finalization commit
- **THEN** every attested archive, canonical-spec, policy, and generated path is
  attributed to the source Change
- **AND** no reader requires a new active Change merely because the official
  active Change list is empty
- **AND** all surfaces select the same finalization scope.

#### Scenario: Missing or tampered archive authority fails closed

- **WHEN** the archive result, effect Attestation, source Commitment, Lease
  generation, or exact path set is absent, ambiguous, stale, or tampered
- **THEN** ETHOS does not project archive-finalization authority
- **AND** it reports the first exact missing coordinate and one public next
  command
- **AND** it does not infer permission from an archive path or historical lane.

#### Scenario: Multi-commit Change start recovers its exact successor

- **GIVEN** a signed Change-start commit is already the first-parent successor
  of the Lease-bound expected HEAD
- **AND** later commits are clean, unique, and covered by the same Commitment
  scope and effect evidence
- **AND** the current Lease still matches the old generation
- **WHEN** the same public start/recovery operation is retried
- **THEN** dry-run reports `ready_to_recover` without mutation
- **AND** apply advances only the exact successor Lease generation and records
  one terminal Attestation
- **AND** no second commit, ref replay, or OpenSpec invocation is performed.

#### Scenario: Finalization state is classified before mutation

- **WHEN** a finalization request observes no Lease, an expired same-holder
  Lease, a different-holder Lease, or an ownerless effect
- **THEN** ETHOS reports distinct machine-readable states
- **AND** an expired same-holder Lease reports the exact public resume command
- **AND** a different-holder Lease reports the public query for an already
  accepted takeover authorization before any takeover command can be formed
- **AND** an ownerless exact effect reports the exact archive recovery command
- **AND** a truly missing Lease with no exact effect fails closed, reports the
  public status command, and marks that a user authority decision is required
- **AND** no command silently assumes holder identity or edits SQLite directly.

#### Scenario: Zero-effect failure has no compensation gap

- **WHEN** preflight fails before a ref, worktree, Lease, or Git object is
  created
- **THEN** the receipt records the original failure and proves each asset
  absent
- **AND** it does not report compensation or cleanup failure for an asset that
  never existed.

#### Scenario: Hook observation cannot re-enter Git maintenance

- **WHEN** a Git reference transaction invokes ETHOS admission while Git holds
  a ref or packed-refs lock
- **THEN** the hook performs only bounded read-only observations that cannot
  launch maintenance or acquire the same lock
- **AND** a missing observation returns `effect_observation_unavailable` with a
  public recovery command rather than hanging.

## ADDED Requirements

### Requirement: Refresh-base replay is signing-bound and compare-and-swap safe

When a Work Lane refresh requires SSH commit signing through a configured
file-backed key, ETHOS SHALL establish signing transport before the replay can
start. It SHALL revalidate the admitted Work Lane and candidate SHA snapshots,
replay the admitted Work Lane SHA against the admitted candidate SHA in
detached state, and compare-and-swap the Work Lane ref from its admitted old
SHA before attaching it again.

#### Scenario: unavailable signing transport blocks before replay

- **GIVEN** `commit.gpgsign` is truthy, `gpg.format` is `ssh`, and
  `user.signingkey` resolves to a file-backed key with no usable agent transport
- **WHEN** `lane refresh-base --apply` runs
- **THEN** it reports `refresh_signing_transport_unavailable`
- **AND** it does not start a rebase or advance the Work Lane ref.

#### Scenario: admitted snapshots move during preflight

- **GIVEN** a refresh has captured Work Lane and candidate SHA values
- **WHEN** either value changes before replay begins
- **THEN** it reports the corresponding `refresh_base_snapshot_stale` gap
- **AND** it does not start a rebase or advance the Work Lane ref.

#### Scenario: Work Lane moves before replay compare-and-swap

- **GIVEN** detached replay has produced a candidate-descended refreshed SHA
- **WHEN** the Work Lane ref no longer equals its admitted old SHA
- **THEN** ETHOS reports `refresh_base_snapshot_stale:work_lane`
- **AND** it reattaches to the newer branch state without overwriting that ref.

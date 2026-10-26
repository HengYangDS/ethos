## MODIFIED Requirements

### Requirement: Generation reclamation uses fresh operational facts

ETHOS SHALL reclaim only exact owned generations without current operational
dependencies. Every destructive step SHALL recheck dependency observations and
directory identity under the selected-runtime fence. Reclamation SHALL report
completed, retained and deferred resources independently from activation. A
listed path deleted while it is observed SHALL count as an observed absence,
not as an unknown observation.

#### Scenario: A consumer appears after initial observation

- **WHEN** a process, config or interpreter binding begins referencing a candidate before its deletion boundary
- **THEN** the fresh observation retains that generation
- **AND** selected and retained generation bytes remain unchanged.

#### Scenario: Historical observations accumulate

- **WHEN** repeated successful activations record paths of superseded runtimes
- **THEN** those historical records alone do not retain the runtimes
- **AND** reclamation neither deletes nor rewrites the historical records
- **AND** repeated cleanup converges without adding generation directories.

#### Scenario: Cleanup observation becomes unavailable

- **WHEN** runtime activation succeeds but a required consumer observation cannot be read
- **THEN** activation remains observable as successful and reclamation is deferred
- **AND** candidates without a completed fresh admission remain untouched
- **AND** the result reports the exact unavailable boundary and a public recovery action.

#### Scenario: A later cleanup step fails

- **WHEN** one generation is removed and a later observation or deletion fails
- **THEN** the report preserves the completed removal and identifies remaining paths
- **AND** retry derives fresh candidates rather than claiming rollback or repeating a vanished effect.

#### Scenario: Selector or candidate identity changes

- **WHEN** the selected runtime or exact candidate directory changes before its destructive effect
- **THEN** reclamation rejects the stale coordinate
- **AND** it does not delete a replacement directory under the old name.

#### Scenario: A listed path is deleted while it is observed

- **WHEN** another process deletes a path that the process listing names while reclamation is observing it
- **THEN** reclamation treats that path as absent and completes
- **AND** a dangling symbolic link that the listing names still defers reclamation
- **AND** a listed path that resolves into a generation still retains that generation.

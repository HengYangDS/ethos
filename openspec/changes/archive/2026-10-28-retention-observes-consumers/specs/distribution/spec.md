## MODIFIED Requirements

### Requirement: Installed product migration preserves live consumers

Installation, upgrade, rollback and uninstall SHALL use exact owned resources and
fresh live-consumer observations. Existing common-directory runtime generations
SHALL remain recoverable until their consumers have migrated. Unknown liveness
SHALL prevent deletion without erasing successful activation evidence. A
repository that has pinned an installation and not yet named it in its
selectors SHALL count as a live consumer of that installation.

#### Scenario: Upgrade is interrupted

- **WHEN** preparation or activation fails between durable effect and acknowledgement
- **THEN** recovery identifies the selected version and preserves the previous usable version
- **AND** it does not repeat a destructive effect from missing acknowledgement alone

#### Scenario: A live repository still references an old installation

- **WHEN** uninstall or reclamation finds a live version consumer
- **THEN** the consumer's selected bytes remain available
- **AND** cleanup reports the exact remaining dependency

#### Scenario: A repository is between pinning and selecting an installation

- **WHEN** reclamation runs while a repository has pinned an installation and not yet named it in `CURRENT` or `ROLLBACK`
- **THEN** that repository's consumer record and the installation remain
- **AND** a later reclamation retires the installation only after the repository's selection settles without naming it

#### Scenario: Reclamation observes a repository without ETHOS state

- **WHEN** reclamation reads a recorded repository whose common directory has no ETHOS state
- **THEN** it creates nothing in that repository
- **AND** it releases the repository's record, because the repository selects nothing

#### Scenario: An external selected runtime has disappeared

- **WHEN** a repository's `CURRENT` names an absent external runtime
- **AND** the invoking installed package is valid for that repository's exact build and lock
- **THEN** installation reuses that package and replaces the stale selection by exact CAS
- **AND** an existing but invalid external target never silently falls back
- **AND** an invalid target is distinguished from an absent target
- **AND** no compatible invoking runtime produces an explicit supply requirement, not
  a command that repeats the missing path

#### Scenario: A complete external installation predates the accepted build

- **WHEN** `CURRENT` selects an intact external runtime for an older build and
  the invoking product has an admitted successor build
- **THEN** installation distinguishes the predecessor's manifest, executable
  and wheel integrity from applicability to the successor source and lock
- **AND** it reuses a compatible invoking package or constructs the new
  source-bound generation before atomically changing selection
- **AND** build or activation failure preserves the previous selection, while
  missing or damaged external supply and foreign private runtimes remain refused

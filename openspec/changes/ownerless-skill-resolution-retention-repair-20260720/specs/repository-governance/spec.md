## MODIFIED Requirements

### Requirement: Durable exceptional-resolution recovery inventory

ETHOS SHALL materialize successful exceptional-resolution decisions, receipts,
preservation manifests, and bounded clear records under a stable local records
owner derived from the configured accepted checkout. The records owner SHALL
survive linked Work Lane retirement. Inventory and clear SHALL retain
read-only compatibility with legacy per-worktree lane-resolution artifacts,
but conflicting records for one decision SHALL fail closed.

#### Scenario: a preserved resolution is discoverable

- **GIVEN** a preserve or preserve-retire decision succeeds
- **WHEN** ETHOS completes the local effect
- **THEN** it writes a schema-validated immutable receipt bound to the observed
  lane, head, decision, and manifest when present
- **AND** inventory reports retained or unindexed state without minting
  authority from an artifact.

#### Scenario: a carrier invokes preservation and is later retired

- **GIVEN** a Work Lane invokes lane_resolution/preserve-retire for an exact
  source observation
- **WHEN** ETHOS writes the decision, package, and completion receipt
- **THEN** those records SHALL be owned by the configured accepted checkout's
  sibling recovery-records root rather than by the invoking Work Lane
- **AND** later retirement of the invoking Work Lane SHALL not remove them
- **AND** accepted-root inventory and package verification SHALL still report
  the retained package after both source and carrier worktrees are absent.

#### Scenario: a legacy Work Lane still owns retained recovery material

- **GIVEN** a linked Work Lane contains an ignored legacy
  build/artifacts/lane-resolution/*/manifest.json
- **WHEN** ordinary landed or superseded retirement reobserves the selected
  worktree
- **THEN** ETHOS SHALL block before removing the worktree, branch ref, or lease
- **AND** it SHALL report that retained lane-resolution recovery material still
  requires migration or an evidence-bound clear.

#### Scenario: duplicate local decision records conflict

- **GIVEN** canonical and legacy stores expose the same decision ID with
  different manifest or receipt content
- **WHEN** inventory or clear is requested
- **THEN** ETHOS SHALL report a machine-readable conflict
- **AND** it SHALL not choose one record by scan order or remove either package.

#### Scenario: final receipt materialization fails after effect

- **GIVEN** a stable decision and verified preservation package exist
- **WHEN** the bounded source transition completes but immutable receipt writing
  fails
- **THEN** ETHOS SHALL report an explicit partial transition
- **AND** the stable decision and package SHALL remain inspectable for
  reconciliation
- **AND** the command SHALL not report ordinary success.

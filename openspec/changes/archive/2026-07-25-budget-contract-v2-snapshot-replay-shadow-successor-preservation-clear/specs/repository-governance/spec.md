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

#### Scenario: immutable decision records cannot collide or redirect ownership

- **GIVEN** a caller records more than one decision for the same branch, or
  supplies a path that already exists
- **WHEN** ETHOS selects or writes the decision path
- **THEN** each default path SHALL be unique and an existing explicit path SHALL
  block with `lane_resolution_decision_path_exists`
- **AND** caller Work Lane policy bytes SHALL NOT redirect the configured
  accepted checkout's sibling records owner.

#### Scenario: a new decision path targets a legacy or unrelated root

- **GIVEN** a caller supplies an explicit decision path outside the configured
  accepted checkout's sibling lane-resolution records root
- **WHEN** ETHOS plans the decision
- **THEN** it SHALL report `lane_resolution_decision_path_not_local_artifact`
- **AND** it SHALL not write into a legacy, foreign-worktree, or unrelated root.

#### Scenario: a tampered decision identifier attempts package path escape

- **GIVEN** a stored decision identifier is not canonical
  `lane-decision:<UUID>` or its package realpath escapes the pinned records root
- **WHEN** ETHOS applies the decision
- **THEN** it SHALL block before package materialization
- **AND** it SHALL not write into a foreign, legacy, or unrelated root.

#### Scenario: an existing package directory cannot be reused

- **GIVEN** the canonical package path for one decision already exists
- **WHEN** ETHOS applies a preserve or preserve-retire decision
- **THEN** it SHALL report `lane_resolution_preservation_package_exists`
- **AND** it SHALL not overwrite any existing recovery bytes.

#### Scenario: a completion receipt is already present or reserved

- **GIVEN** the deterministic completion-receipt destination already exists or
  another conforming writer owns its hidden reservation sidecar
- **WHEN** ETHOS applies a preserve-retire decision
- **THEN** it SHALL report `lane_resolution_receipt_path_exists` before package,
  ref, or worktree mutation
- **AND** it SHALL preserve the existing bytes, branch, and linked worktree.

#### Scenario: receipt reservation follows the effect boundary

- **GIVEN** ETHOS exclusively reserves a completion-receipt destination
- **WHEN** preparation fails before effect or final receipt materialization
  succeeds
- **THEN** it SHALL release the reservation
- **AND** when a destructive effect completes but final receipt writing fails,
  it SHALL retain the reservation for reconciliation and still enforce the
  final writer's no-clobber check.

#### Scenario: a package or record path contains a symlink component

- **GIVEN** a package, manifest, receipt, or clear-record path redirects through
  a symlink
- **WHEN** ETHOS inventories, writes, verifies, or clears resolution records
- **THEN** it SHALL report `lane_resolution_package_path_unsafe` or
  `lane_resolution_record_path_unsafe`
- **AND** it SHALL not write or delete outside the pinned records owner.

#### Scenario: a legacy Work Lane still owns retained recovery material

- **GIVEN** a linked Work Lane contains an ignored legacy
  build/artifacts/lane-resolution/*/manifest.json
- **WHEN** ordinary landed or superseded retirement reobserves the selected
  worktree
- **THEN** ETHOS SHALL block with `lane_resolution_legacy_retention_present`
  before removing the worktree, branch ref, or lease
- **AND** it SHALL report that retained lane-resolution recovery material still
  requires migration or an evidence-bound clear.

#### Scenario: duplicate local decision records conflict

- **GIVEN** canonical and legacy stores expose the same decision ID with
  different manifest or receipt content
- **WHEN** inventory or clear is requested
- **THEN** ETHOS SHALL report `lane_resolution_decision_record_conflict`
- **AND** it SHALL not choose one record by scan order or remove either package.

#### Scenario: byte-identical package copies make clear ambiguous

- **GIVEN** more than one physical package location exposes the same decision ID
  and manifest bytes
- **WHEN** clear is requested
- **THEN** ETHOS SHALL report `lane_resolution_clear_package_ambiguous`
- **AND** it SHALL not remove only the scan-order-selected copy.

#### Scenario: durable manifest and receipt binding diverges

- **GIVEN** a retained manifest digest no longer matches its immutable receipt
- **WHEN** inventory, verification, or clear reads durable records
- **THEN** ETHOS SHALL report `lane_resolution_manifest_receipt_mismatch`
- **AND** it SHALL not report the package as consistently retained or cleared.

#### Scenario: final receipt materialization fails after effect

- **GIVEN** a stable decision and verified preservation package exist
- **WHEN** the bounded source transition completes but immutable receipt writing
  fails
- **THEN** ETHOS SHALL report `ok=false`, `state=partial_transition`, and
  `lane_resolution_receipt_write_failed_after_effect`
- **AND** the stable decision and package SHALL remain inspectable for
  reconciliation
- **AND** the exclusive receipt reservation SHALL remain present for explicit
  reconciliation
- **AND** the command SHALL not report ordinary success.

#### Scenario: one absorbed detached-residue package is cleared by exact manifest

- **GIVEN** an accepted Chronicle selects
  `lane_resolution/clear-preservation` for one exact decision id and manifest
- **AND** the retained tracked patch matches the pre-effect capture, the index
  patch is empty, no untracked archive exists, and accepted behavior contains
  no missing capability from that package
- **WHEN** a maintainer invokes native clear with the matching manifest,
  non-empty reason, break-glass, and irreversible confirmation
- **THEN** ETHOS SHALL re-read inventory and manifest bytes before removing only
  that package and emitting a clear receipt
- **AND** the original decision and completion receipt SHALL remain
- **AND** another package, a changed manifest, raw deletion, or batch clear
  SHALL remain blocked.

#### Scenario: one absorbed snapshot-replay package is cleared by exact manifest

- **GIVEN** an accepted Chronicle selects
  `lane_resolution/clear-preservation` for one exact decision id and manifest
- **AND** the native tracked patch reconstructs the pre-effect full-index dirty
  tree, the index patch is empty, no untracked archive exists, and accepted
  behavior contains no missing capability from that package
- **WHEN** a maintainer invokes native clear with the matching manifest,
  non-empty reason, break-glass, and irreversible confirmation
- **THEN** ETHOS SHALL re-read inventory and manifest bytes before removing only
  that package and emitting a clear receipt
- **AND** the original decision and completion receipt SHALL remain
- **AND** another package, a changed manifest, raw deletion, batch clear, or
  source reconstruction SHALL remain blocked.

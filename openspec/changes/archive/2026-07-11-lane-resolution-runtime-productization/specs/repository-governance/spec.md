## ADDED Requirements

### Requirement: Discoverable local lane-resolution receipts

ETHOS SHALL materialize every successful exceptional lane-resolution receipt as
a schema-validated immutable local artifact and SHALL expose a read-only
inventory over receipts, preservation manifests, and clear receipts.

#### Scenario: a preserved lane has a discoverable receipt

- **GIVEN** a `preserve` or `preserve-retire` decision succeeds
- **WHEN** ETHOS completes the effect
- **THEN** it writes an atomic receipt bound to the decision, observed lane,
  observation digest, and preservation manifest when present
- **AND** `ethos lane resolution inventory --json` reports the retained package
  without treating the artifact as authority

#### Scenario: a historical package has no materialized receipt

- **GIVEN** a valid legacy preservation manifest exists without a receipt
- **WHEN** inventory is requested
- **THEN** ETHOS reports the package as unindexed rather than hiding it or
  inventing a receipt

### Requirement: Evidence-bound recovery-package clearing

ETHOS SHALL delete a retained lane-resolution package only through an exact,
manifest-bound, Chronicle-gated manual-clear transition.

#### Scenario: manual clear is accepted

- **GIVEN** an accepted Chronicle contains `lane_resolution/clear-preservation`
  and the selected package's manifest matches its supplied SHA-256
- **WHEN** a maintainer supplies a reason, break-glass, and irreversible
  confirmation
- **THEN** ETHOS records a clear receipt and removes only that exact package
- **AND** the prior resolution receipt and accepted Chronicle remain intact

#### Scenario: clear input is stale or incomplete

- **WHEN** the manifest digest, Chronicle binding, reason, break-glass, or
  irreversible confirmation is missing or mismatched
- **THEN** ETHOS reports a required gap and leaves the package intact

### Requirement: Source-bound Work Lane runner bootstrap

ETHOS SHALL give each newly started Work Lane a runner-bootstrap contract that
uses the lane's own source and semantic generated homes.

#### Scenario: a lane uses the official runner

- **WHEN** an operator runs the returned runner command from the Work Lane
- **THEN** uv project state is placed under `build/runtime/venv`
- **AND** uv cache is placed under `build/runtime/tool-cache/uv`
- **AND** the executable imports ETHOS from that Work Lane rather than an
  unrelated installed checkout

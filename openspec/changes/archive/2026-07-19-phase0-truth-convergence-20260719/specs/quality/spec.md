## ADDED Requirements

### Requirement: Coverage writer evidence is fail-closed

ETHOS SHALL report Python coverage policy, configuration, current artifact, and
writer ownership without allowing an unverified lock to satisfy or defer the
hard coverage floor.

#### Scenario: Active writer remains blocking until evidence exists

- **WHEN** `ethos quality coverage --json` observes a missing coverage artifact
  and a writer lock with a parseable owner PID and matching live process-start
  fingerprint
- **THEN** it SHALL report `state=in_progress`
- **AND** it SHALL report a blocking `coverage_artifact_write_in_progress` gap
- **AND** report, prove, enterprise readiness, and local publication SHALL NOT
  treat the coverage gate as clean until the artifact exists.

#### Scenario: Invalid or stale writer does not hide missing evidence

- **WHEN** the coverage writer lock lacks owner metadata, contains malformed
  metadata, names a dead PID, or names a reused PID with a different process
  start
- **THEN** ETHOS SHALL retain `coverage_artifact_missing`
- **AND** it SHALL expose the observed lock state without claiming an active
  writer.

#### Scenario: Test owner script recovers invalid stale locks safely

- **WHEN** the Python test owner script encounters a proven-dead writer
- **THEN** it SHALL reclaim the lock and continue
- **AND** when owner metadata remains missing or malformed for the complete
  bounded wait, it MAY reclaim that persistently invalid lock once and retry
- **AND** it SHALL never preempt a valid live owner.

### Requirement: Product hard-quality floor covers current generated state

ETHOS SHALL include generated-artifact topology in the product hard-quality
floor consumed by scorecard and local publication readiness.

#### Scenario: Current generated-artifact drift blocks green readiness

- **WHEN** `ethos quality generated-artifacts --json` reports required gaps
- **THEN** `ethos report --json` SHALL include those gaps in the hard-quality
  layer
- **AND** product `ethos publish --json` SHALL report local readiness blocked
- **AND** an earlier HEAD-bound proof SHALL NOT override the current local-state
  blocker.

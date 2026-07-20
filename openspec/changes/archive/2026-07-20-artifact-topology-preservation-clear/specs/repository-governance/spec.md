## MODIFIED Requirements

### Requirement: Durable exceptional-resolution recovery inventory

ETHOS SHALL materialize successful exceptional-resolution receipts under a
semantic local-artifact home and SHALL expose a read-only inventory over
receipts, preservation manifests, and bounded clear records.

#### Scenario: one superseded preservation package is cleared without erasing audit history

- **GIVEN** an accepted Chronicle selects
  `lane_resolution/clear-preservation` for one decision id, one package, and
  one exact manifest SHA-256
- **AND** current accepted proof shows the retained patch contributes no unique
  product behavior
- **WHEN** a maintainer invokes native clear with the matching manifest,
  non-empty reason, break-glass, and irreversible confirmation
- **THEN** ETHOS SHALL re-validate the exact package before removing only that
  package and emit a clear receipt
- **AND** the original decision and completion receipt SHALL remain
- **AND** another package, a manifest mismatch, raw deletion, or a batch clear
  SHALL remain blocked.

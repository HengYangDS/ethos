## ADDED Requirements

### Requirement: Bounded evidence-carrier debt remains explicit

ETHOS SHALL account for a temporary active evidence-carrier footprint through a
named source-budget debt record rather than a per-file exemption or baseline
reset.

#### Scenario: A compact active claim is introduced

- **WHEN** an active claim and its mandatory carrier metadata exceed the
  currently available source-budget slack
- **THEN** any temporary allowance SHALL name its owner, replacement, deletion
  wave, expiry, and exact allowance
- **AND** it SHALL remain within the existing maximum debt
- **AND** formatting policy MAY keep declarative arrays compact without changing
  the claim schema or its trust boundary.

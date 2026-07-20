## MODIFIED Requirements

### Requirement: Productized OpenSpec carrier governance

ETHOS SHALL treat OpenSpec as the repository case and specification carrier,
with accepted specs, active changes, archived changes, capability profiles,
claims, and evidence refs serving distinct product duties. Archive closeout
SHALL preserve accepted scenario obligations unless an explicit removal decision
carries the deletion. Archive closeout SHALL reject non-canonical or duplicate
logical archive identities.

#### Scenario: Archive closeout is a product gate

- **WHEN** a Work Lane depends on a previously closed OpenSpec carrier
- **THEN** that prior carrier is archived through the official OpenSpec archive
  path before downstream campaign steps depend on it
- **AND** claims that refer to the carrier point at the dated archive path after
  archive closeout
- **AND** accepted specification obligations are fused forward rather than
  deleted by a tool-applied archive delta
- **AND** removing an accepted `WHEN`, `THEN`, or `AND` obligation requires an
  explicit removal decision instead of silent replacement.
- **AND** the campaign manifest records the lane as closed and retired before
  the next campaign step becomes active.

#### Scenario: Archive identity is canonical and unique

- **WHEN** archive closeout evaluates historical carriers
- **THEN** each name SHALL be `YYYY-MM-DD-<date-free-logical-id>`
- **AND** each logical ID SHALL resolve to exactly one archive carrier
- **AND** numeric-leading, terminal-date, and duplicate logical identities
  SHALL block closeout without compatibility aliases or date selection.

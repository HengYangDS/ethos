## MODIFIED Requirements

### Requirement: Quality Asset Model

ETHOS SHALL model repository assets across code, docs, shell, configuration,
evidence, release artifacts, and adopter profiles. The tracked tool catalog
SHALL be the sole declaration of a quality tool's identity, profile, adoption
state, configuration, and optional gate boundary.

#### Scenario: Asset policy is reported

- **WHEN** `ethos quality asset-policy --json` runs
- **THEN** ETHOS reports asset classes, dimensions, and catalog-derived tool
  profiles without executing provider tools

#### Scenario: Tool profiles are catalog-derived

- **WHEN** `ethos quality tool-profiles --json` or
  `ethos quality asset-policy --json` reports quality tool adapters
- **THEN** every adapter is derived from exactly one `system/tools.toml` entry
- **AND** its concern, tool identity, configuration, profile, adoption state,
  and optional gate agree with that entry
- **AND** the tools contract requires an adoption state of `active`,
  `candidate`, `deferred`, or `rejected`
- **AND** no parallel static Python tool-adapter registry supplies conflicting
  tool truth

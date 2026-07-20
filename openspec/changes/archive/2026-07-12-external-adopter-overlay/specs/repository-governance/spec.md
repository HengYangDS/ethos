## ADDED Requirements

### Requirement: Explicit non-destructive adopter overlay

ETHOS SHALL preserve strict adoption as the default and SHALL offer an explicit
overlay mode for an existing repository whose governance surfaces must remain
adopter-owned.

#### Scenario: Strict adoption sees differing adopter governance

- **WHEN** `ethos adopt` runs without overlay mode and a scaffolded target path
  already has differing nonempty content
- **THEN** the plan SHALL report `adoption_conflict:<path>`
- **AND** apply SHALL refuse to write any scaffold file.

#### Scenario: Overlay preserves declared adopter-owned surfaces

- **WHEN** `ethos adopt --overlay` runs against an existing repository with a
  differing AGENTS entrypoint, documentation, OpenSpec workspace, or selected
  hosted-provider projection
- **THEN** the plan SHALL classify each declared adopter-owned path as preserved
- **AND** apply SHALL leave its bytes unchanged
- **AND** apply SHALL create each missing ETHOS-owned binding surface.

#### Scenario: Overlay records the preserved identity

- **WHEN** overlay planning preserves an existing adopter-owned surface
- **THEN** command JSON SHALL include its path and SHA-256 content digest
- **AND** that record SHALL describe a non-mutated boundary rather than claim
  semantic compatibility or authority.

#### Scenario: Overlay does not override ETHOS-owned state

- **WHEN** `ethos adopt --overlay` encounters differing nonempty content in an
  ETHOS-owned `.ethos/**`, `.config/ethos/**`, ETHOS skill-package, or schema
  placeholder path
- **THEN** the plan SHALL report `adoption_conflict:<path>`
- **AND** apply SHALL refuse to write any scaffold file.

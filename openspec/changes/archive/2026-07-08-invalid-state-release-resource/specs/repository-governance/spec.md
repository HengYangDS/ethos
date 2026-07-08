## MODIFIED Requirements

### Requirement: Invalid-State Taxonomy Is Source Truth And Release-Usable

ETHOS SHALL keep the invalid-state taxonomy source of truth in
`system/invalid_states.toml` while ensuring installed `ethos-core` package
artifacts can load an equivalent release mirror when no source checkout is
available.

#### Scenario: Source checkout keeps the SSOT

- **GIVEN** `system/invalid_states.toml` exists in the repository checkout
- **WHEN** `ethos_core.invalid_states.invalid_state_categories()` loads the taxonomy
- **THEN** it reads the source contract
- **AND** the packaged mirror does not become an independent authority

#### Scenario: Installed wheel keeps taxonomy available

- **GIVEN** `ethos-core` runs outside a repository checkout
- **WHEN** the invalid-state taxonomy is loaded
- **THEN** `ethos_core/data/invalid_states.toml` supplies the same parsed taxonomy
- **AND** tests verify the release mirror matches `system/invalid_states.toml`

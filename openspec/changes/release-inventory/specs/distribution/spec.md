## ADDED Requirements

### Requirement: A published runtime archive declares what it ships

Each hosted release SHALL publish two inventories for every runtime archive: an SPDX 2.3 SBOM and a Syft JSON inventory with Go symbols, each naming the archive's published file and SHA-256 and listing its components. Publication SHALL refuse any archive whose inventories name another digest or file or are declared twice, refuse a required archive without both, leave out and name an optional archive without both, and attest them.

#### Scenario: An archive's inventories match its bytes

- **WHEN** a release leg's inventories name its archive's published name and digest and list its expected components
- **THEN** the release publishes both beside the archive, covered by `SHA256SUMS` and the build provenance attestation

#### Scenario: An optional archive's declaration is incomplete

- **WHEN** a Windows release leg uploads only one of its two inventories
- **THEN** that archive is not published
- **AND** the release notes and the assembler's output name its host

#### Scenario: A binding does not match

- **WHEN** any release leg's inventory names another digest or file, or a second declaration sits beside the two
- **THEN** assembly fails with `release_assets_inventory_mismatch:<host>`, for an optional host too

#### Scenario: A one-package SBOM

- **WHEN** an inventory lists only the archive itself
- **THEN** assembly fails with `release_assets_inventory_components_missing:<host>`

#### Scenario: An expected component is missing

- **WHEN** the catalog lacks the locked `uv` crate, a declared Go tool's module, Node or a shipped Python distribution
- **THEN** the inventory owner refuses and names the missing component

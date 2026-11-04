## ADDED Requirements

### Requirement: A published runtime archive declares what it ships

Each hosted release SHALL publish two inventories for every runtime archive: an SPDX 2.3 SBOM and a Syft JSON inventory with Go symbols. Each SHALL name the archive's published file name and SHA-256 and list its components, complete against their owners. Publication SHALL refuse a required archive whose inventories are missing, name another digest or list no component, and SHALL attest both inventories.

#### Scenario: An archive's inventories match its bytes

- **WHEN** a release leg's inventories name its archive's published name and digest and list its expected components
- **THEN** the release publishes both beside the archive, covered by `SHA256SUMS` and the build provenance attestation

#### Scenario: A one-package SBOM

- **WHEN** an inventory lists only the archive itself
- **THEN** assembly fails with `release_assets_inventory_components_missing:<host>`

#### Scenario: An expected component is missing

- **WHEN** the catalog lacks the locked `uv` crate, a declared Go tool's module, Node or a shipped Python distribution
- **THEN** the inventory owner refuses and names the missing component

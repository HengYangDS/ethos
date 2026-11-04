## ADDED Requirements

### Requirement: A published runtime archive declares what it ships

Each hosted release SHALL publish two inventories for every runtime archive: an SPDX 2.3 SBOM and a Syft JSON inventory with Go symbols. Each SHALL name the archive's published file name and SHA-256 and list its components. Publication SHALL refuse an archive whose inventories are missing, name another digest or list no component, and SHALL attest each SPDX against its archive.

#### Scenario: An archive's inventories match its bytes

- **WHEN** a release leg's inventories name its archive's published name and digest and list its components
- **THEN** the release publishes both beside the archive, covered by `SHA256SUMS`
- **AND** an SBOM attestation binds the SPDX to the archive's digest

#### Scenario: A one-package SBOM

- **WHEN** an inventory lists only the archive itself
- **THEN** assembly fails with `release_assets_inventory_components_missing:<host>`

### Requirement: A release run reports the binary-level advisories of what it shipped

After publication, a read-only hosted job SHALL check each published Syft inventory against `SHA256SUMS` and scan it with the pinned Grype. Its report SHALL name the scanner and database, each archive's digest, one row per archive, package, version and advisory, and the executables with no identified package. The scan SHALL NOT block the release.

#### Scenario: A release run scans what it shipped

- **WHEN** a hosted release run has published its archives and inventories
- **THEN** its report lists each archive's digest and the advisories that Grype matched in its inventory
- **AND** the release itself does not wait for the report

#### Scenario: An inventory is missing

- **WHEN** a host's archive is published without its Syft inventory
- **THEN** the report names that host as not scanned
- **AND** never reports zero findings for it

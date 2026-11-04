## ADDED Requirements

### Requirement: A release run reports the binary-level advisories of what it shipped

After publication, a read-only hosted job SHALL check each published Syft inventory against `SHA256SUMS` and the archive it names, and scan it with the pinned Grype. Its report SHALL name the scanner and database, each archive's digest, one row per archive, package, version and advisory, and the executables with no identified package. The scan SHALL NOT block the release.

#### Scenario: A release run scans what it shipped

- **WHEN** a hosted release run has published its archives and inventories
- **THEN** its report lists each archive's digest and the advisories that Grype matched in its inventory
- **AND** the release itself does not wait for the report

#### Scenario: An inventory is missing

- **WHEN** a host's archive is published without its Syft inventory
- **THEN** the report names that host as not scanned
- **AND** never reports zero findings for it

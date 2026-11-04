## ADDED Requirements

### Requirement: A release run reports the binary-level advisories of what it shipped

After publication, a hosted release run SHALL catalog each published runtime archive, checked against the release's checksums, with the pinned Syft, and SHALL scan that catalog with the pinned Grype. Its report SHALL name the scanner and database, each archive's digest, and one row per archive, package, version and advisory. The scan SHALL NOT block the release.

#### Scenario: A release run scans what it shipped

- **WHEN** a hosted release run has published its archives
- **THEN** its report lists each archive's digest and the advisories that Grype matched in it
- **AND** the release itself does not wait for the report

#### Scenario: An archive is missing

- **WHEN** a host's archive is absent from the release
- **THEN** the report names that host as not scanned
- **AND** never reports zero findings for it

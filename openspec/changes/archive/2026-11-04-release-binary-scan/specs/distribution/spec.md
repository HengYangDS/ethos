## ADDED Requirements

### Requirement: A release run reports the binary-level advisories of what it shipped

After publication, and on demand for a published release, a read-only hosted job SHALL check each Syft inventory against `SHA256SUMS` and its archive, and scan it with the pinned Grype. Its report SHALL name the scanner, the database's build time, source and checksum, each archive's digest, one row per archive, package, version and advisory, and unidentified executables. The scan SHALL NOT block the release.

#### Scenario: A release run scans what it shipped

- **WHEN** a hosted release run has published its archives and inventories
- **THEN** its report lists each archive's digest and the advisories that Grype matched in its inventory
- **AND** the release itself does not wait for the report

#### Scenario: A published release is scanned again

- **WHEN** a `scan_tag` dispatch names an already published release
- **THEN** only the scan job runs, over that release's published inventories
- **AND** its report records the database that produced it

#### Scenario: An inventory is missing

- **WHEN** a host's archive is published without its Syft inventory
- **THEN** the report names that host as not scanned
- **AND** never reports zero findings for it

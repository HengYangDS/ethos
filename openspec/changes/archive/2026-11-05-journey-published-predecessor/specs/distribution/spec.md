## MODIFIED Requirements

### Requirement: The journey installs only verified release bytes

The journey SHALL check each archive it installs against its release's checksums, and the prerelease's archive against its build attestation, before installing it. The previous release SHALL be the first earlier changelog entry whose release the forge published; the receipt SHALL name each entry it skipped. Each leg SHALL upload its receipt and stage events whether it passes or fails.

#### Scenario: A published archive does not match its release

- **WHEN** a downloaded archive's digest differs from its release checksums, or the prerelease's
  archive fails attestation verification
- **THEN** the journey fails before it installs that archive
- **AND** the leg still uploads its receipt and stage events.

#### Scenario: An earlier version was tagged but never published

- **WHEN** the changelog entry after the prerelease names a version that has no published release
- **THEN** the journey upgrades from the next earlier version whose release exists
- **AND** its receipt names the skipped version.

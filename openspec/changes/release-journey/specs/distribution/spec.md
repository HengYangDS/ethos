## ADDED Requirements

### Requirement: A hosted journey qualifies each published prerelease

After a release run publishes a prerelease, a hosted journey SHALL install its published artifacts
through Mise on macOS and Linux and pass, in fixture adopters on fresh host stores, a cold install,
host-store pinning, hook binding, a full proof and status, an upgrade from the previous release with
its rollback, and uninstall. A dispatch SHALL run the journey alone for an already published
prerelease.

#### Scenario: A prerelease is published

- **WHEN** a release run publishes a prerelease
- **THEN** the journey runs on macOS and Linux against its published assets
- **AND** each leg's receipt names the result of every journey step.

#### Scenario: A published prerelease is qualified again

- **WHEN** a dispatch names an already published prerelease for the journey alone
- **THEN** only the journey runs, and the release is not published again.

### Requirement: The journey installs only verified release bytes

The journey SHALL check each archive it installs against its release's checksums, and the
prerelease's archive against its build attestation, before installing it. The previous release
SHALL be the one whose changelog entry follows the prerelease's. Each leg SHALL upload its receipt
and stage events whether it passes or fails.

#### Scenario: A published archive does not match its release

- **WHEN** a downloaded archive's digest differs from its release checksums, or the prerelease's
  archive fails attestation verification
- **THEN** the journey fails before it installs that archive
- **AND** the leg still uploads its receipt and stage events.

## ADDED Requirements

### Requirement: A beta's journey starts from every release that adopters select

A beta's journey evidence SHALL include an upgrade, with its rollback, from the previous release and from every earlier published release that a governed adopter still selects. Release preparation SHALL name those releases from the adopters' own declarations, because ETHOS keeps no registry of them.

#### Scenario: A governed adopter selects an older release

- **WHEN** a governed adopter still selects a published release older than the previous release
- **THEN** a beta's journey evidence includes an upgrade from that release with its rollback
- **AND** without that evidence, the beta is not qualified for that adopter.

### Requirement: A journey dispatch may name its predecessors

A dispatch that runs the journey alone MAY name earlier published prereleases as its predecessors. Each named predecessor SHALL be a prerelease tag whose changelog entry is earlier than the prerelease's and whose release the forge published; otherwise the journey SHALL refuse, naming it, before it downloads anything. The journey SHALL upgrade from each predecessor, and roll back to it, in its own host store.

#### Scenario: A dispatch names the predecessors

- **WHEN** a dispatch names two earlier published prereleases as predecessors
- **THEN** each leg upgrades from each of them, and rolls back to it, in its own host store
- **AND** the cold install, the full proof and the uninstall run once per leg
- **AND** each leg's receipt names both predecessors, their verified assets and each upgrade's
  result.

#### Scenario: A named predecessor is not an earlier published release

- **WHEN** a dispatch names a predecessor whose changelog entry is not earlier than the
  prerelease's, or whose release the forge never published
- **THEN** the journey refuses with that predecessor's tag before it downloads anything
- **AND** the leg still uploads its receipt and stage events.

## MODIFIED Requirements

### Requirement: Prereleases advance on declared journey evidence

A product-release target SHALL declare the journeys it supports, and its
prereleases SHALL advance by evidence on those journeys, not by age or landing
count. An alpha is any accepted increment. A beta SHALL have hosted verification
passing on every supported platform for its release head, the declared adopter
journey passing from the published artifacts on macOS and Linux, and no known
defect that corrupts an installation, blocks a landing or admits a wrong proof.

#### Scenario: A prerelease is promoted to beta

- **WHEN** release preparation selects a beta for the declared target
- **THEN** hosted verification has passed on every supported platform for the
  release head
- **AND** the published artifacts have passed, on macOS and Linux, a cold
  install, host-store pinning, hook binding, a full proof and status, an upgrade
  with its rollback from each predecessor that a beta's journey requires, and
  uninstall
- **AND** no known defect corrupts an installation, blocks a landing or admits a
  wrong proof.

### Requirement: A hosted journey qualifies each published prerelease

After a release run publishes a prerelease, a hosted journey SHALL install its published artifacts
through Mise on macOS and Linux and pass, in fixture adopters on fresh host stores, a cold install,
host-store pinning, hook binding, a full proof and status, an upgrade from each predecessor with its
rollback, and uninstall. A dispatch SHALL run the journey alone for an already published
prerelease.

#### Scenario: A prerelease is published

- **WHEN** a release run publishes a prerelease
- **THEN** the journey runs on macOS and Linux against its published assets
- **AND** each leg's receipt names the result of every journey step.

#### Scenario: A published prerelease is qualified again

- **WHEN** a dispatch names an already published prerelease for the journey alone
- **THEN** only the journey runs, and the release is not published again.

### Requirement: The journey installs only verified release bytes

The journey SHALL check each archive it installs against its release's checksums, and the prerelease's archive against its build attestation, before installing it. Without named predecessors, the previous release SHALL be the first earlier changelog entry whose release the forge published; the receipt SHALL name each entry it skipped. Each leg SHALL upload its receipt and stage events whether it passes or fails.

#### Scenario: A published archive does not match its release

- **WHEN** a downloaded archive's digest differs from its release checksums, or the prerelease's
  archive fails attestation verification
- **THEN** the journey fails before it installs that archive
- **AND** the leg still uploads its receipt and stage events.

#### Scenario: An earlier version was tagged but never published

- **WHEN** the changelog entry after the prerelease names a version that has no published release
- **THEN** the journey upgrades from the next earlier version whose release exists
- **AND** its receipt names the skipped version.

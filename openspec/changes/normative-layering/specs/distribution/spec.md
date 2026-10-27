## ADDED Requirements

### Requirement: Product versions follow the declared compatibility surface

The public compatibility surface SHALL be the documented CLI arguments, exit
codes and structured output, SDK contracts, MCP tools and resources,
configuration, and persisted repository-state contracts, not private
implementation. Review of changes to it SHALL select the increment. Before
1.0.0, an incompatible release line SHALL take a minor increment, numbered
prereleases SHALL iterate toward the declared target, and release notes SHALL
name each incompatibility and its migration.

#### Scenario: An incompatible change precedes 1.0.0

- **GIVEN** the latest released product version is 0.2.0
- **WHEN** accepted changes alter a documented CLI exit code incompatibly
- **THEN** release preparation selects the 0.3.0 line, reached through numbered
  prereleases
- **AND** the release entry names the incompatibility and its migration.

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
  from the previous release with its rollback, and uninstall
- **AND** no known defect corrupts an installation, blocks a landing or admits a
  wrong proof.

### Requirement: Release candidates and stable releases follow adopter use

A release candidate SHALL be a beta that adopters used for 72 hours without a
new blocking defect; from the first release candidate on, only fixes SHALL land
toward the target. A stable release SHALL be a release candidate that adopters
used for 7 days without a blocking defect. The release entry SHALL name each
journey the target does not declare, or whose environment was unavailable, as
not qualified; neither such a journey nor an adopter's own adoption SHALL gate
the release.

#### Scenario: A journey is outside the declared target

- **GIVEN** the target does not declare GitLab-hosted CI
- **WHEN** its release is prepared
- **THEN** the release entry names GitLab-hosted CI as not qualified
- **AND** its absence does not block the release.

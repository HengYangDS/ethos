## ADDED Requirements

### Requirement: The hosted journey runs on every declared host

The hosted journey SHALL run one leg on each host whose journey the release target declares. Each
leg SHALL run on a runner of its own architecture, without emulation, and SHALL qualify the
published archive of its own platform.

#### Scenario: The target declares three hosts

- **GIVEN** the release target declares journeys on Linux x64, Linux arm64 and macOS arm64
- **WHEN** a release run publishes a prerelease, or a dispatch names a published one for the
  journey alone
- **THEN** the journey runs one leg on Linux x64, one on Linux arm64 and one on macOS arm64

#### Scenario: The Linux arm64 leg runs

- **WHEN** the Linux arm64 leg runs
- **THEN** it runs on a native arm64 runner
- **AND** its receipt names the platform `linux-arm64`

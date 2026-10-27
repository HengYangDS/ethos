## MODIFIED Requirements

### Requirement: Package Manager Isolation

Distribution adapters SHALL remain outside the Python distribution declared by
the repository-root `pyproject.toml`.

#### Scenario: uv workspace remains Python-only

- **WHEN** the repository contains a Node distribution adapter under
  `distributions/npm`
- **THEN** the wheel package remains `src/ethos`
- **AND** `distributions/npm` launcher metadata does not alter Python builds

### Requirement: Exact Node Runtime Compatibility Policy

ETHOS SHALL select exactly one Node release in `.config/mise/config.toml`,
verify its official archive against `.config/mise/mise.lock`, and execute hosted
npm acceptance through `tools/ci/toolchain/npm.py` and the `javascript_tests` Nox
session rather than provider-inline npm command bodies.

#### Scenario: Hosted npm compatibility is executed for an exact release

- **WHEN** a hosted npm acceptance job runs
- **THEN** Node is the single release pinned in `.config/mise/config.toml`
- **AND** its official archive matches the `mise.lock` SHA-256 before extraction
- **AND** `tools/ci/toolchain/npm.py` enables npm engine-strict behavior and runs
  `npm ci --ignore-scripts` and `npm run ethos -- --version`, then
  `nox -s javascript_tests` runs `npm run test:npm`
- **AND** hosted provider YAML invokes the reusable owner instead of restating
  the acceptance command body.

### Requirement: Reviewed Node Default Promotion

ETHOS SHALL keep hosted compatibility verification separate from its single
mise-pinned Node release and SHALL require a separate reviewed change to move
that pin.

#### Scenario: Compatibility expands without promoting packaging

- **WHEN** a Node release is added only to hosted compatibility verification
- **THEN** the `.config/mise/config.toml` Node pin and the Node packaged in the
  wheel remain unchanged
- **AND** promotion requires current release-status verification, successful
  hosted compatibility results, package evidence, and a separate reviewed
  repository change.

#### Scenario: Current stable release becomes the packaging default

- **WHEN** a newer stable Node release has current upstream release evidence and
  passes the hosted npm acceptance
- **THEN** a separate reviewed change moves the `.config/mise/config.toml` pin, and
  its lock and the Node packaged in the wheel follow that pin
- **AND** no second compatibility release is retained beside the pin.

## ADDED Requirements

### Requirement: Hosted package construction uses runner supply and one Node resolver

ETHOS SHALL take hosted prerequisites from the runner environment, which for
GitLab's Linux jobs is the locked supply image, and SHALL install no host
prerequisite at bootstrap. It SHALL resolve Node from the `mise.lock`-verified
official archive and npm from the locked product module through one validated
resolver that every source-build, package-only runtime, OpenSpec, and delivery
consumer uses.

#### Scenario: A GitLab Linux job runs in the locked supply image

- **GIVEN** a GitLab Linux job runs in the locked supply image
- **WHEN** repository bootstrap starts
- **THEN** Git, `libatomic1`, and `openssh-client` are present at the versions
  that `.config/ci/supply/Dockerfile` pins
- **AND** bootstrap installs no host prerequisite.

#### Scenario: Windows build resolves the installed Node layout

- **GIVEN** the `mise.lock`-verified Node archive is installed on Windows
- **WHEN** runtime materialization, OpenSpec, or delivery binds Node inputs
- **THEN** Node resolves to the distribution-root `node.exe`
- **AND** npm resolves to the locked npm module's `npm-cli.js` when npm is required
- **AND** the coordinates are validated before their consumer executes.

#### Scenario: POSIX build resolves the installed Node layout

- **GIVEN** the `mise.lock`-verified Node archive is installed on a supported
  POSIX host
- **WHEN** runtime materialization, OpenSpec, or delivery binds Node inputs
- **THEN** Node resolves to the distribution's `bin/node`
- **AND** npm resolves to the locked npm module's `npm-cli.js` when npm is required
- **AND** callers do not reconstruct either coordinate.

## REMOVED Requirements

### Requirement: Hosted package construction uses platform-native locked inputs

**Reason**: Its bootstrap script (`tools/ci/scripts/bootstrap-python.sh`, deleted in `cbf439019`) no longer repairs Linux prerequisites with `apt-get`, and `nodejs-wheel` left the lock in `41a75140c`. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Hosted package construction uses runner supply and one Node resolver".

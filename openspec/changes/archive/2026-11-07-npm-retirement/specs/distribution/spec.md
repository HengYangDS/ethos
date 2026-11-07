## MODIFIED Requirements

### Requirement: Exact Node Runtime Compatibility Policy

ETHOS SHALL select exactly one Node release in `.config/mise/config.toml` for its JavaScript tools,
verify its official archive against `.config/mise/mise.lock`, and execute hosted Node acceptance
through `tools/ci/toolchain/npm.py` and the `javascript_tests` Nox session rather than
provider-inline npm command bodies.

#### Scenario: Hosted npm compatibility is executed for an exact release

- **WHEN** a hosted JavaScript acceptance job runs
- **THEN** Node is the single release pinned in `.config/mise/config.toml`
- **AND** its official archive matches the `mise.lock` SHA-256 before extraction
- **AND** `tools/ci/toolchain/npm.py` enables npm engine-strict behavior and runs
  `npm ci --ignore-scripts`, then `nox -s javascript_tests` runs the repository's JavaScript tests
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
  passes the hosted Node acceptance
- **THEN** a separate reviewed change moves the `.config/mise/config.toml` pin, and
  its lock and the Node packaged in the wheel follow that pin
- **AND** no second compatibility release is retained beside the pin.

## ADDED Requirements

### Requirement: Root Node manifests stay unpublishable

The root `package.json`, which declares the repository's JavaScript tools, SHALL stay private when
it declares workspaces and SHALL carry no person attribution metadata, so no Node manifest can
publish product assets.

#### Scenario: A root package declares workspaces

- **WHEN** `ethos prove --gate product-boundary --json` audits the root `package.json`
- **THEN** a root package that declares workspaces without `private: true` is reported
- **AND** author, authors, maintainers, and contributors metadata are absent

## REMOVED Requirements

### Requirement: Published Distribution Boundary

**Reason**: Its allowlist governed the npm launcher's published files, and the launcher is
retired; the root manifest rule moves to "Root Node manifests stay unpublishable".

**Migration**: None.

### Requirement: Launcher Adapter Boundary

**Reason**: The npm launcher, the only distribution adapter it governed, is retired (R8(f)).

**Migration**: Run the installed `ethos` or `uv run ethos` from a checkout.

### Requirement: Package Manager Isolation

**Reason**: No Node distribution adapter remains to isolate from the Python build.

**Migration**: None; the wheel stays `src/ethos`.

### Requirement: Distribution Adapter Outside Python Packages

**Reason**: The npm launcher package under `distributions/npm` is removed.

**Migration**: None.

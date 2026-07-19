# ETHOS Distribution

## Purpose

ETHOS SHALL expose package-manager launchers without moving command semantics
out of the canonical command plane.
## Requirements
### Requirement: Launcher Adapter Boundary
Distribution adapters SHALL forward to the ETHOS command plane and SHALL NOT
define independent governance behavior.

#### Scenario: npm launcher uses command plane
- **WHEN** a user invokes the npm launcher from an ETHOS source checkout
- **THEN** it executes the Python `ethos` command plane through the repository
  environment
- **AND** the Node package remains a launcher-only adapter

### Requirement: Package Manager Isolation
Distribution adapters SHALL be excluded from Python workspace package discovery
unless they are Python packages themselves.

#### Scenario: uv workspace remains Python-only
- **WHEN** the repository contains a Node distribution adapter under
  `distributions/npm`
- **THEN** uv workspace members list the Python packages explicitly
- **AND** package-manager metadata does not break Python builds

### Requirement: Published Distribution Boundary
Distribution manifests SHALL publish only neutral launcher assets and SHALL NOT
ship historical evidence, host-local state, tests, adopter-private records, or
person attribution metadata as product defaults.

#### Scenario: npm package scope is allowlisted
- **WHEN** `ethos quality product-boundary --json` audits distribution manifests
- **THEN** the root workspace package is non-publishable
- **AND** the npm distribution manifest declares an explicit `files` allowlist
- **AND** that allowlist is limited to launcher assets and neutral package docs
- **AND** author, authors, maintainers, and contributors metadata are absent

### Requirement: Distribution Adapter Outside Python Packages
ETHOS SHALL keep npm launcher metadata under `distributions/npm` and outside
the Python package workspace.

#### Scenario: npm launcher is checked
- **WHEN** npm workspace metadata is inspected
- **THEN** it references `distributions/npm`
- **AND** it does not reference `packages/ethos-node`
- **AND** the launcher forwards to the Python ETHOS command plane

### Requirement: Exact Node Runtime Compatibility Policy

ETHOS SHALL keep exact npm-launcher compatibility releases in one repository
policy and SHALL execute hosted compatibility acceptance through one reusable
runner rather than provider-inline npm command bodies.

#### Scenario: Hosted npm compatibility is executed for an exact release

- **WHEN** a hosted npm compatibility job runs
- **THEN** `.config/checks/node/runtime.toml` declares Node 24.18.0 and Node
  26.5.0 as the exact compatibility set
- **AND** the provider selects one declared release through `NODE_VERSION`
- **AND** the installer verifies the selected official archive against a
  policy-pinned SHA-256 value before extraction
- **AND** `tools/ci/scripts/run-node-compatibility.sh` rejects an active-runtime
  mismatch before npm executes
- **AND** the runner enables npm engine-strict behavior and executes
  `npm ci --ignore-scripts`, `npm run ethos -- --version`, and
  `npm run test:npm` in that order
- **AND** hosted provider YAML invokes the reusable owner instead of restating
  the acceptance command body

### Requirement: Reviewed Node Default Promotion

ETHOS SHALL keep compatibility expansion separate from hosted packaging-default
promotion and SHALL require a reviewed change for any default transition.

#### Scenario: Compatibility expands without promoting packaging

- **WHEN** Node 26.5.0 is added to hosted compatibility verification
- **THEN** Node 24.18.0 remains the runtime policy default
- **AND** the npm packaging job continues to use the Node 24.18.0 installer
  default
- **AND** Node 26.5.0 is recorded only as the next default candidate
- **AND** 2026-10-28 is an earliest review trigger, not an automatic transition
- **AND** promotion requires current release-status verification, successful
  hosted compatibility results, package evidence, and a separate reviewed
  repository change

### Requirement: Node Runtime Authority Boundary

ETHOS distribution compatibility policy SHALL govern repository proof releases
without claiming mutation authority over separately managed runtime owners.

#### Scenario: Managed runtimes remain outside repository mutation

- **WHEN** workstation, IDE, desktop, application, and hosted Node runtimes are
  inventoried
- **THEN** the repository compatibility policy governs only declared launcher
  proof and hosted projection behavior
- **AND** workstation software supply remains workstation-owned
- **AND** IDE-, desktop-, and application-managed runtimes remain owned by their
  respective applications
- **AND** repository compatibility work does not rewrite those managed runtimes

### Requirement: Release configuration advertises only active policy

ETHOS release configuration and adopter scaffolds SHALL expose only fields that
are consumed by active release policy and SHALL derive artifact homes from the
canonical generated-artifact topology.

#### Scenario: Release configuration is loaded

- **WHEN** product or adopter release policy reads `.ethos/release.toml`
- **THEN** protected refs, host surfaces, publication remotes, and attestation
  policy remain available
- **AND** dead `version_source`, `tag_pattern`, and `artifact_glob = "dist/*"`
  fields are not generated or treated as configurable behavior.

#### Scenario: Distribution output is located

- **WHEN** a build or release operation resolves Python artifacts
- **THEN** it uses the canonical `build/artifacts/python` topology
- **AND** root `dist/*` is not advertised as a supported artifact home.

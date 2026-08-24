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
Distribution adapters SHALL remain outside the Python distribution declared by
the repository-root `pyproject.toml`.

#### Scenario: uv workspace remains Python-only
- **WHEN** the repository contains a Node distribution adapter under
  `distributions/npm`
- **THEN** the wheel package remains `src/ethos`
- **AND** Node package-manager metadata does not alter Python builds

### Requirement: Published Distribution Boundary
Distribution manifests SHALL publish only neutral launcher assets and SHALL NOT
ship historical evidence, host-local state, tests, adopter-private records, or
person attribution metadata as product defaults.

#### Scenario: npm package scope is allowlisted
- **WHEN** `ethos prove --gate product-boundary --json` audits distribution manifests
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
- **AND** it is not included in the Python wheel
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

- **WHEN** host, IDE, desktop, application, and hosted Node runtimes are
  inventoried
- **THEN** the repository compatibility policy governs only declared launcher
  proof and hosted projection behavior
- **AND** host software supply remains host-owned
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

### Requirement: hook installation retires the legacy runtime locator

After the final package-only runtime manifest, public entrypoint, and hook
launchers validate, hook installation SHALL remove the common-directory
`ethos-runtime-python` legacy locator whether it is a regular file or symlink.
The receipt SHALL report the locator disposition. Failure before validation
SHALL leave the locator untouched.

#### Scenario: obsolete locator survives from a source launcher

- **WHEN** successful hook installation finds `ethos-runtime-python` in the Git common directory
- **THEN** it removes the locator and reports it as retired without changing runtime or SQLite authority

#### Scenario: runtime validation fails

- **WHEN** the final runtime manifest or launcher validation fails
- **THEN** hook installation fails closed and does not remove the legacy locator

### Requirement: Source runtime uses the locked closure
ETHOS SHALL install source-built runtimes from `uv.lock` offline.
#### Scenario: Lock unavailable
- **WHEN** the lock cannot supply the production closure
- **THEN** installation SHALL fail without fallback or network resolution.

### Requirement: Package-only hook runtime carries accepted source identity
Every non-editable ETHOS wheel used to materialize a Git-hook runtime SHALL carry
one immutable build identity containing the exact ETHOS source commit and source
tree. The runtime manifest SHALL bind that identity together with its wheel,
Python ABI, platform, executable, and entrypoint bytes.

#### Scenario: wheel is built from an ETHOS checkout
- **WHEN** a non-editable wheel is built from a Git-backed ETHOS source tree
- **THEN** the wheel contains its exact source commit and source tree as package data
- **AND** an installed runtime copies those values into its single manifest identity

#### Scenario: runtime is installed without a source checkout
- **WHEN** hook installation runs from an installed wheel outside an ETHOS source checkout
- **THEN** it derives source identity from the wheel's packaged build identity
- **AND** it does not require a live checkout, host-local database, or absolute build path

#### Scenario: legacy manifest lacks source identity
- **WHEN** runtime observation encounters the retired integrity-only manifest schema
- **THEN** the runtime is non-current and cannot authorize hook execution
- **AND** the reader returns the public repair action rather than invoking a compatibility reader

### Requirement: Selected package runtime is the executable authority

A governed repository SHALL select exactly one validated immutable package runtime under its Git common directory. Package-only commands and generated Git hooks SHALL execute that selected runtime without consulting ambient `PATH`, a source checkout, or another mutable runtime registry.

#### Scenario: package command is absent from PATH
- **WHEN** a governed repository has a valid selected package runtime and `ethos` is absent from `PATH`
- **THEN** its generated hook and public remediation command execute the selected runtime by absolute path
- **AND** both identify the same runtime digest and source identity.

#### Scenario: selector is missing or malformed
- **WHEN** the runtime selector is absent, unreadable, non-canonical, or identifies a runtime whose manifest or files do not validate
- **THEN** package execution and governed mutation fail before invoking another runtime
- **AND** no ambient executable or historical launcher binding is used as fallback.

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

ETHOS SHALL keep exact current LTS and current npm-launcher compatibility
releases in one repository policy and SHALL execute hosted compatibility
acceptance through one reusable runner rather than provider-inline npm command
bodies.

#### Scenario: Hosted npm compatibility is executed for an exact release

- **WHEN** a hosted npm compatibility job runs
- **THEN** `.config/checks/node/runtime.toml` declares Node 24.20.0 and Node
  26.8.1 as the exact compatibility set
- **AND** the provider selects one declared release through `NODE_VERSION`
- **AND** the installer verifies the selected official archive against a
  policy-pinned SHA-256 value before extraction
- **AND** `tools/ci/scripts/run-node-compatibility.sh` rejects an active-runtime
  mismatch before npm executes
- **AND** the runner enables npm engine-strict behavior and executes
  `npm ci --ignore-scripts`, `npm run ethos -- --version`, and
  `npm run test:npm` in that order
- **AND** hosted provider YAML invokes the reusable owner instead of restating
  the acceptance command body.

### Requirement: Reviewed Node Default Promotion

ETHOS SHALL keep compatibility expansion separate from hosted packaging-default
promotion and SHALL require a reviewed change for any default transition.

#### Scenario: Compatibility expands without promoting packaging

- **WHEN** a Node release is added only to hosted compatibility verification
- **THEN** the existing runtime policy and npm packaging default remain
  unchanged
- **AND** promotion requires current release-status verification, successful
  hosted compatibility results, package evidence, and a separate reviewed
  repository change.

#### Scenario: Current stable release becomes the packaging default

- **WHEN** Node 26.8.1 has current upstream release evidence and passes the
  declared hosted compatibility acceptance
- **THEN** Node 26.8.1 becomes the runtime policy and npm packaging default
- **AND** Node 24.20.0 remains the exact LTS compatibility release
- **AND** future default changes still require current release-status
  verification, package evidence, and a separate reviewed repository change.

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

ETHOS SHALL treat `uv.lock` as the dependency-resolution authority, the active
lock-current source environment as bootstrap supply, the Git-common immutable
runtime as the minimal production projection, and uv cache state as disposable.
Before using the active environment for a non-isolated source build, ETHOS SHALL
verify that environment against the lock. It SHALL then prune a copied runtime
to the hash-bound production closure, install the exact source-built ETHOS
wheel, and preserve the installed distribution's unique public console-script
entrypoints in the resulting image. Validation failure SHALL precede runtime
selection or hook activation.

#### Scenario: Empty cache with a lock-current source environment

- **WHEN** source-checkout hook installation runs offline with an empty uv cache
  and the active environment matches `uv.lock`
- **THEN** ETHOS builds the wheel from that verified environment
- **AND** installs a runtime containing the locked production closure and exact
  ETHOS wheel without network or cache dependence.

#### Scenario: Active source environment drift

- **WHEN** the active source environment does not match `uv.lock`
- **THEN** installation fails before producing or selecting a runtime or hook
  generation
- **AND** it does not fall back to network resolution, ambient cache contents,
  or an unverified interpreter.

#### Scenario: Lock unavailable

- **WHEN** the lock cannot define or verify the production closure
- **THEN** installation fails before producing or selecting a runtime or hook
  generation
- **AND** it does not fall back to network resolution or an unlocked closure.

#### Scenario: Package-only runtime materialization

- **WHEN** hook installation runs from a provenance-bound installed wheel rather
  than a source checkout
- **THEN** it continues to materialize the runtime from that package closure
- **AND** it resolves the exact wheel from the selected runtime's Git-common
  content-addressed package store
- **AND** it discovers the unique `ethos` console entrypoint from the installed
  wheel metadata on every supported host
- **AND** it does not require uv, a source environment, a repository lock, a
  host-specific launcher fallback, or a still-existing predecessor repository
  path.

#### Scenario: Package-only wheel provenance is incomplete

- **WHEN** the selected runtime's content-addressed wheel is missing, ambiguous,
  or does not match its manifest digest
- **THEN** successor materialization fails before runtime or hook activation
- **AND** it does not fall back to a stale `direct_url.json`, PATH package, cache,
  or network source.

### Requirement: Package-only hook runtime carries accepted source identity
Every non-editable ETHOS wheel used to materialize a Git-hook runtime SHALL carry
one immutable build identity containing the exact ETHOS source commit and source
tree. The runtime manifest SHALL bind that identity together with its wheel,
Python ABI, operating system, CPU architecture, executable, and entrypoint bytes.

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

### Requirement: Package build temporary supply has a bounded owner

The OpenSpec build hook SHALL own temporary supply until the build target has
consumed declared `force_include` inputs.

#### Scenario: Successful build finalization reclaims supply

- **WHEN** a wheel or source build reaches finalization
- **THEN** the exact build-owned supply directory no longer exists.

#### Scenario: Build initialization failure reclaims supply

- **WHEN** initialization fails after supply allocation
- **THEN** the exact build-owned supply directory no longer exists
- **AND** the original failure remains observable.

#### Scenario: Editable build allocates no supply

- **WHEN** the hook initializes an editable build
- **THEN** it creates no OpenSpec supply directory.

### Requirement: Product version has one repository authority
ETHOS SHALL keep one tracked SemVer product-version value, SHALL advance that
value whenever accepted product semantics advance incompatibly with the prior
prerelease identity, and SHALL derive every publishable distribution version
and manifest projection from that value.

#### Scenario: Repository manifests are inspected
- **WHEN** Python, root workspace, and launcher package metadata are compared
- **THEN** they resolve to the one product-version authority
- **AND** no manifest retains an independently editable product-version literal.

#### Scenario: Accepted prerelease semantics advance
- **WHEN** a newly accepted runtime contains product semantics not represented
  by the previously accepted prerelease
- **THEN** the repository product version advances to a greater SemVer value
- **AND** exact source and artifact digests remain additional identities rather
  than substitutes for that version.

### Requirement: Product, source, and artifact identities remain distinct
ETHOS SHALL represent product version, distribution version, exact source
commit/tree, wheel digest, and runtime digest without treating Git repository
acceptance as package-release state.

#### Scenario: Accepted repository source is built
- **WHEN** the current accepted Git commit is used to install a hook runtime
- **THEN** its wheel has a unique PEP 440 development version bound to that commit and tree
- **AND** no release Attestation is minted.

#### Scenario: Package-only runtime is inspected
- **WHEN** ETHOS runs without access to its source checkout
- **THEN** its immutable manifest reports product and distribution versions,
  source commit/tree, wheel SHA256, runtime digest, interpreter ABI, operating
  system, and CPU architecture
- **AND** no field is inferred from Git branch role, mutable host path, or Forge state.

### Requirement: Unreleased builds are unique and comparable
ETHOS SHALL derive every source-checkout build from the next product version and
exact Git source identity, regardless of checkout role.

#### Scenario: Successive accepted commits share one next release target
- **WHEN** two accepted commits are built before the explicit release transition
- **THEN** their distribution identities differ and sort before the exact release
- **AND** the newer runtime can replace the older runtime without version-reuse conflict.

#### Scenario: Two source commits are built before release
- **WHEN** two distinct source commits share the same next product version
- **THEN** their distribution identities differ and remain PEP 440 parseable
- **AND** neither artifact claims the exact release identity.

### Requirement: Accepted release identity is immutable
ETHOS SHALL create an exact release identity only from an explicit release
transition and SHALL reject rollback, source reuse, or artifact disagreement.

#### Scenario: Ordinary runtime installation occurs
- **WHEN** hook installation builds or selects a source development wheel
- **THEN** release admission and release Attestation are not invoked.

#### Scenario: Explicit release is admitted
- **WHEN** a release transition presents the exact normalized release version, source, and wheel
- **THEN** admission occurs before effect
- **AND** Attestation occurs only after fresh post-observation.

#### Scenario: Existing accepted version is rebuilt from different source
- **WHEN** a release request presents a previously accepted version with a
  different source tree or wheel digest
- **THEN** release admission blocks with a stable version-reuse conflict
- **AND** no package, tag, runtime selector, or remote projection changes.

#### Scenario: Runtime identity schema changes after a release
- **WHEN** a release Attestation issued under an earlier release-predicate payload schema is read
- **THEN** its exact immutable release fact remains valid authority for rollback and reuse admission
- **AND** retired runtime fields do not reappear in the current build or runtime identity.

#### Scenario: Local-only release is admitted
- **WHEN** an explicit release has no configured Forge
- **THEN** local repository and artifact evidence can establish the same version fact
- **AND** a Forge tag or release is an optional projection, not the version owner.

### Requirement: Hosted package construction uses platform-native locked inputs

ETHOS SHALL bootstrap hosted prerequisites from the observed operating system
and SHALL resolve `nodejs-wheel` Node/npm inputs through one product-owned,
validated resolver used by every source-build, package-only runtime, OpenSpec,
and delivery consumer. It SHALL NOT infer a Debian host from a missing Linux
utility or reconstruct package paths independently at each caller.

#### Scenario: Darwin bootstrap does not enter Debian installation

- **GIVEN** the shared Python bootstrap executes on Darwin with Git available
- **WHEN** Linux `ldconfig` is unavailable
- **THEN** the bootstrap does not invoke `apt-get`
- **AND** it continues through the repository-locked Python and OpenSpec setup.

#### Scenario: Linux bootstrap repairs supported prerequisites

- **GIVEN** the shared Python bootstrap executes on Linux
- **WHEN** Git, `libatomic.so.1`, or the signing policy's `ssh-keygen` executable
  is missing and `apt-get` is available
- **THEN** it installs only the corresponding declared host prerequisite before
  repository bootstrap continues
- **AND** absence of the selected package manager fails with a precise diagnostic.

#### Scenario: Windows wheel build resolves the installed Node layout

- **GIVEN** `nodejs-wheel-binaries` is installed from the repository lock on Windows
- **WHEN** runtime materialization, OpenSpec, or delivery binds Node inputs
- **THEN** Node resolves to the package-root `node.exe`
- **AND** npm resolves to the package-local `npm-cli.js` when npm is required
- **AND** the coordinates are validated before their consumer executes.

#### Scenario: POSIX wheel build resolves the installed Node layout

- **GIVEN** `nodejs-wheel-binaries` is installed from the repository lock on a
  supported POSIX host
- **WHEN** runtime materialization, OpenSpec, or delivery binds Node inputs
- **THEN** Node resolves to the package-local `bin/node`
- **AND** npm resolves to the package-local `npm-cli.js` when npm is required
- **AND** callers do not reconstruct either coordinate.

### Requirement: Content-addressed package publication is host portable

ETHOS SHALL publish immutable package bytes with file durability, atomic
identity establishment, and collision verification on every supported host.
It SHALL apply an additional parent-directory durability barrier only where the
host supports opening and synchronizing directory descriptors.

#### Scenario: Windows publishes an immutable package

- **WHEN** ETHOS materializes a content-addressed package on Windows
- **THEN** it flushes the complete file and atomically establishes the digest path
- **AND** it does not attempt the unsupported POSIX directory-descriptor operation.

#### Scenario: POSIX preserves the directory durability barrier

- **WHEN** ETHOS materializes a content-addressed package on a supported POSIX host
- **THEN** it synchronizes the containing directory after atomic publication
- **AND** any directory open or synchronization failure remains fatal.

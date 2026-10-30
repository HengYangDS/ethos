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
- **AND** `distributions/npm` launcher metadata does not alter Python builds

### Requirement: Published Distribution Boundary

Distribution manifests SHALL publish only neutral launcher assets and SHALL NOT
ship historical evidence, host-local state, tests, adopter-private records, or
person attribution metadata as product defaults.

#### Scenario: npm package scope is allowlisted

- **WHEN** `ethos prove --gate product-boundary --json` audits distribution manifests
- **THEN** a root package that declares workspaces is non-publishable
- **AND** the npm distribution manifest declares an explicit `files` allowlist
- **AND** that allowlist is limited to launcher assets and neutral package docs
- **AND** author, authors, maintainers, and contributors metadata are absent

### Requirement: Distribution Adapter Outside Python Packages

ETHOS SHALL keep npm launcher metadata under `distributions/npm` and outside
the Python package workspace.

#### Scenario: npm launcher is checked

- **WHEN** the npm launcher package is inspected
- **THEN** it is the standalone package at `distributions/npm`, not a workspace of the root package
- **AND** it is not included in the Python wheel
- **AND** the launcher forwards to the Python ETHOS command plane

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

`uv.lock` SHALL own resolution; the exact source root's lock-current `.venv`
SHALL supply builds and dependency bytes; Git-common runtime SHALL be the minimal
production projection; uv caches SHALL be disposable. Before non-isolated builds,
ETHOS SHALL verify the full locked build closure, export hashed non-dev supply,
prune the runtime to it, install the exact ETHOS wheel and retain unique public
console scripts. Failure SHALL precede selector or hook activation.

#### Scenario: Empty cache with a lock-current source environment

- **WHEN** source-checkout hook installation runs offline with an empty uv cache
  and the target checkout root `.venv` matches the complete `uv.lock` closure
- **THEN** ETHOS builds the wheel through that verified environment
- **AND** installs a runtime containing the locked production closure and exact
  ETHOS wheel without network or cache dependence.

#### Scenario: Active source environment drift

- **WHEN** the target checkout root `.venv` does not match `uv.lock`, including
  the build backend and locked uv package
- **THEN** installation fails before producing or selecting a runtime or hook
  generation
- **AND** it does not fall back to network resolution, ambient cache contents,
  or an unverified interpreter.

#### Scenario: Older runtime activates newer source

- **GIVEN** the selected immutable runtime predates the target source build
  backend or dependency closure
- **WHEN** it coordinates activation for that exact source checkout
- **THEN** the target checkout root `.venv` supplies locked uv, the build
  backend, the complete build closure, and installed dependency bytes
- **AND** the selected runtime is not required to contain or emulate the newer
  source closure.

#### Scenario: Lock unavailable

- **WHEN** the lock cannot define or verify the build and production closures
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

Non-editable hook-runtime wheels SHALL carry immutable source commit/tree
identity. Clean checkouts SHALL yield that tree on every supported host under
repository Git content semantics. Outside a selected runtime, installed wheels
SHALL resolve their source wheel from the PEP 610 `file:` URL with native path
semantics before identity validation. Runtime manifests SHALL bind that identity,
wheel, Python ABI, OS, CPU architecture, executable and entrypoint bytes.

#### Scenario: wheel is built from an ETHOS checkout

- **WHEN** a non-editable wheel is built from a Git-backed ETHOS source tree
- **THEN** the wheel contains its exact source commit and source tree as package data
- **AND** an installed runtime copies those values into its single manifest identity

#### Scenario: clean source checkout crosses host text defaults

- **GIVEN** two supported hosts check out the same exact ETHOS commit under
  different ambient text-conversion defaults
- **WHEN** each host compiles the source build identity without a real overlay
- **THEN** both identities contain the commit's exact `HEAD^{tree}` value
- **AND** checkout presentation does not create a host-specific distribution version

#### Scenario: installed wheel uses a native file URL

- **WHEN** a provenance-bound installed distribution reports its originating
  wheel through a valid local PEP 610 `file:` URL
- **THEN** ETHOS converts that URL through the current host's native path semantics
- **AND** validates and reuses that exact wheel without a source checkout or
  platform-specific path rewrite

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

ETHOS SHALL derive product-release projections from one tracked SemVer 2.0.0
target. Unpublished source iterations MAY share it. Once an explicit release
identity is accepted, changed released semantics SHALL require a greater
version. Source and artifact digests SHALL NOT replace that
release boundary. No dependency lock SHALL record the product version.

#### Scenario: Repository manifests are inspected

- **WHEN** Python, root package, and launcher package metadata are compared
- **THEN** they resolve to the one product-version authority
- **AND** no manifest retains an independently editable product-version literal
- **AND** the root package lock records no product version

#### Scenario: A release advances the product version

- **WHEN** release preparation moves the product version
- **THEN** no dependency lock or supply-image input changes
- **AND** the locked supply image built before it still matches the release checkout

#### Scenario: Unpublished source iterations share a release target

- **WHEN** several accepted source commits precede explicit release
- **THEN** they may retain the same next product-release target
- **AND** their exact development build identities remain distinct

#### Scenario: Accepted prerelease semantics advance

- **WHEN** newly accepted product semantics are selected after an explicitly released prerelease
- **THEN** the product version advances according to the compatibility policy
- **AND** the existing release version and artifacts remain unchanged

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

### Requirement: Prepared Node supply identity is dependency-bound

ETHOS SHALL validate a reusable prepared Node supply against the locked
`node_modules/*` dependency closure and SHALL NOT treat root or linked workspace
metadata as installed dependency bytes.

#### Scenario: Product version advances without dependency change

- **WHEN** the repository product version changes while every locked
  `node_modules/*` package entry remains identical
- **THEN** the existing prepared Node supply remains valid
- **AND** ETHOS does not require another install or another supply tree.

#### Scenario: Installed dependency changes

- **WHEN** any locked `node_modules/*` package entry differs from the prepared
  supply lock
- **THEN** ETHOS rejects that supply as a lock mismatch.

### Requirement: Native trust preflight preserves identity and failure meaning

Host qualification SHALL check required native trust primitives before building
or installing candidate packages. Windows ACL admission SHALL compare native SIDs
without account-name round trips. Missing environment, missing executable, process
creation, timeout and ACL rejection SHALL remain distinguishable; none permits
signing or publication. Native platform acceptance remains independently required.

#### Scenario: A native prerequisite fails

- **WHEN** native trust or executable preflight fails on a selected platform
- **THEN** no candidate build or installation starts
- **AND** the native failure reason remains visible without retry or permissive fallback

#### Scenario: A foreign SID has no resolvable account name

- **WHEN** an ACL grants write access to a foreign SID without a resolvable account name
- **THEN** admission rejects the foreign write authority directly from the SID
- **AND** valid current-user protection remains admissible on the native platform

### Requirement: Host installation and repository selection are distinct

ETHOS SHALL be installable outside its source checkout. Host installation SHALL
own reusable immutable version supply; repository bindings SHALL select exact
identities and retain repository-local policy and Git state. Adoption SHALL NOT
copy the product source or require ETHOS developer tools.

#### Scenario: Two repositories select installed supply

- **WHEN** two repositories select the same installed identity
- **THEN** they reuse immutable product bytes without sharing mutable repository state
- **AND** a repository selecting a different version remains unchanged

### Requirement: Installed product migration preserves live consumers

Installation, upgrade, rollback and uninstall SHALL use exact owned resources and
fresh live-consumer observations. Existing common-directory runtime generations
SHALL remain recoverable until their consumers have migrated. Unknown liveness
SHALL prevent deletion without erasing successful activation evidence. A
repository that has pinned an installation and not yet named it in its
selectors SHALL count as a live consumer of that installation.

#### Scenario: Upgrade is interrupted

- **WHEN** preparation or activation fails between durable effect and acknowledgement
- **THEN** recovery identifies the selected version and preserves the previous usable version
- **AND** it does not repeat a destructive effect from missing acknowledgement alone

#### Scenario: A live repository still references an old installation

- **WHEN** uninstall or reclamation finds a live version consumer
- **THEN** the consumer's selected bytes remain available
- **AND** cleanup reports the exact remaining dependency

#### Scenario: A repository is between pinning and selecting an installation

- **WHEN** reclamation runs while a repository has pinned an installation and not yet named it in `CURRENT` or `ROLLBACK`
- **THEN** that repository's consumer record and the installation remain
- **AND** a later reclamation retires the installation only after the repository's selection settles without naming it

#### Scenario: Reclamation observes a repository without ETHOS state

- **WHEN** reclamation reads a recorded repository whose common directory has no ETHOS state
- **THEN** it creates nothing in that repository
- **AND** it releases the repository's record, because the repository selects nothing

#### Scenario: An external selected runtime has disappeared

- **WHEN** a repository's `CURRENT` names an absent external runtime
- **AND** the invoking installed package is valid for that repository's exact build and lock
- **THEN** installation reuses that package and replaces the stale selection by exact CAS
- **AND** an existing but invalid external target never silently falls back
- **AND** an invalid target is distinguished from an absent target
- **AND** no compatible invoking runtime produces an explicit supply requirement, not
  a command that repeats the missing path

#### Scenario: A complete external installation predates the accepted build

- **WHEN** `CURRENT` selects an intact external runtime for an older build and
  the invoking product has an admitted successor build
- **THEN** installation distinguishes the predecessor's manifest, executable
  and wheel integrity from applicability to the successor source and lock
- **AND** it reuses a compatible invoking package or constructs the new
  source-bound generation before atomically changing selection
- **AND** build or activation failure preserves the previous selection, while
  missing or damaged external supply and foreign private runtimes remain refused

### Requirement: Installing released supply is not publishing a release

Repository runtime selection SHALL validate the exact supplied package without
requiring or creating the publisher's release Attestation in the adopter.
Same-version source and wheel conflicts SHALL be rejected across runtime targets;
same-target closure conflicts SHALL preserve the previous selection. Explicit
runtime rollback SHALL NOT be treated as publication of an older version.

#### Scenario: A fresh adopter selects a released runtime

- **WHEN** an admitted installation selects a valid released package in a repository with no product-release Attestations
- **THEN** it selects the exact runtime without creating a product-release claim
- **AND** package validation, selector CAS and repository-local policy remain enforced

#### Scenario: A release version is presented with incompatible bytes

- **WHEN** another available runtime reuses the release version with different source, wheel or same-target closure
- **THEN** activation rejects the conflict and preserves the previous selector
- **AND** changing the interpreter target does not excuse source or wheel disagreement

### Requirement: Independent product acceptance exercises delivered artifacts

Acceptance SHALL execute installed CLI and real MCP client paths outside ETHOS
source, including valid and denied outcomes and repository isolation, with
upgrade and rollback when a predecessor runtime is supplied. A wheel build,
import or source-only test SHALL NOT be reported as complete installed-product
acceptance.

#### Scenario: A candidate builds without an MCP round trip

- **WHEN** package construction succeeds but no installed client journey has passed
- **THEN** artifact construction is recorded separately
- **AND** installed-product acceptance remains incomplete

#### Scenario: Acceptance setup invokes official OpenSpec

- **WHEN** an acceptance fixture archives a Change through official OpenSpec
- **THEN** it uses the existing transport and exact archive-result validator
- **AND** child telemetry and update checks are disabled without changing host preferences
- **AND** its deadline does not exceed the transport bound
- **AND** timeout output is diagnostic, not a completed archive or permission to continue

### Requirement: Platform support is established by native delivered behavior

ETHOS SHALL deliver native macOS and Linux support on explicitly declared
architecture and OS baselines. Windows support SHOULD be provided when qualified.
Required-platform delivery SHALL NOT depend on an unqualified Windows path. A host
platform MAY be served by a runtime that its operating system emulates, only after
that host qualifies those exact bytes. Runtime identity and tool supply SHALL name
the architecture that the interpreter executes, not the host CPU.

#### Scenario: A release advertises supported platforms

- **WHEN** a platform is included in the release support declaration
- **THEN** its delivered artifact passes native installation, CLI/MCP and hooks
- **AND** unsupported combinations remain explicit rather than inheriting another platform's proof

#### Scenario: An emulating host qualifies an x64 runtime

- **WHEN** the release leg that declares `windows-arm64` qualifies the x64 runtime it built
- **THEN** the release declares `windows-arm64` with the archive that leg qualified
- **AND** no wheel is published for `windows-arm64`

#### Scenario: An emulated interpreter selects its runtime

- **WHEN** an x64 interpreter that Windows on Arm emulates selects its runtime
- **THEN** the runtime's recorded architecture is `x86_64`, as its interpreter executes
- **AND** the `ARM64` CPU that the operating system reports does not refuse the selection

### Requirement: Public channels consume explicitly accepted release artifacts

ETHOS SHALL project one accepted product-release version to public channels and
its matching signed tag. Published artifacts SHALL be immutable. Development
build identities SHALL remain exact local selections, not automatic channel
upgrade versions. Pre-release and stable delivery SHALL remain distinct.

#### Scenario: A development archive is proposed for publication

- **WHEN** an archive carries a source-development identity
- **THEN** public release admission rejects it before publication
- **AND** local artifact qualification does not become a release claim

#### Scenario: Release artifacts are prepared

- **WHEN** an explicit release request selects accepted source and a product version
- **THEN** the existing builder produces that release identity before artifact verification
- **AND** the release, signed tag and channel projections identify the same frozen source

#### Scenario: A release candidate is selected for installation qualification

- **WHEN** explicit release arguments select exact accepted-source candidate bytes
- **THEN** the existing offline installation workload verifies those bytes without substitution
- **AND** its separate receipt binds build identity and preserves default development evidence
- **AND** qualification does not accept, notarize or publish the release

#### Scenario: A hosted platform qualifies a signed release

- **WHEN** a hosted runner without the repository proof builds or qualifies release bytes
- **THEN** only the trusted signed tag of that exact clean source, its committed version and
  curated entry admit the release identity
- **AND** an unsigned, untrusted, misplaced or mismatched tag is refused before any build effect
- **AND** publication carries only the wheels and archives whose qualification evidence
  matches their bytes

#### Scenario: Selected package bytes change during qualification

- **WHEN** a selected wheel is missing, redirected or differs from its bound bytes or build
- **THEN** qualification rejects it before effects or before producing passing evidence
- **AND** pre-execution rejection preserves existing work and unrelated development evidence

### Requirement: Curated release notes follow Keep a Changelog

ETHOS SHALL follow Keep a Changelog 1.1.0 for user-facing release notes.
Release preparation SHALL verify an exact-version entry with a valid ISO release
date and applicable change categories. Upcoming changes SHALL remain under
Unreleased until selected for explicit release.

#### Scenario: A release is prepared from Unreleased changes

- **WHEN** an exact accepted source is selected for explicit release
- **THEN** its version entry uses YYYY-MM-DD and meaningful Added, Changed, Deprecated, Removed, Fixed or Security sections
- **AND** missing, duplicate, mismatched or malformed target entries block that release
- **AND** ordinary source acceptance may retain Unreleased notes without claiming publication

#### Scenario: Historical release evidence is unavailable

- **WHEN** an earlier entry lacks a verifiable tag or publication record
- **THEN** the uncertainty remains explicit and historical content is preserved
- **AND** no tag, date or release claim is invented to make the changelog appear complete

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

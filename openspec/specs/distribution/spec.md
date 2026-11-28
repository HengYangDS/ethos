# ETHOS Distribution

## Purpose

ETHOS SHALL expose package-manager launchers without moving command semantics
out of the canonical command plane.

## Requirements

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

ETHOS SHALL create an exact release identity only from an explicit release transition and SHALL
reject rollback, source reuse, or artifact disagreement. A release first accepted with its checksum
file SHALL bind the version, the source commit and tree, that file's digest, and the name and
digest of every wheel and archive the file lists. Readers SHALL admit an identity recorded
without that binding, and a version SHALL keep the identity it first recorded.

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

#### Scenario: A release is accepted with its checksum file

- **WHEN** an explicit release transition presents the release's `SHA256SUMS` with the wheel, for a
  version that has no recorded identity
- **THEN** the accepted identity binds the product version, the source commit and tree, the SHA-256
  of `SHA256SUMS`, and the name and digest of every wheel and archive that file lists
- **AND** the release Attestation names the checksum file's digest among its evidence
- **AND** a transition without the file records the identity as before.

#### Scenario: An identity recorded without the checksum binding is read

- **WHEN** a release Attestation whose payload carries no checksum file digest is read
- **THEN** it yields the same accepted identity as before the binding existed
- **AND** a later acceptance of the same version, source and wheel with its checksum file is
  admitted, and the recorded identity stands.

#### Scenario: One version is presented with two checksum files

- **WHEN** a release request presents an accepted version whose bound checksum file digest differs
  from the one already accepted
- **THEN** release admission blocks with the version's artifact conflict
- **AND** no package or Attestation changes.

#### Scenario: A recorded version is accepted again

- **WHEN** an explicit release transition presents the source and wheel of a version whose identity
  is recorded, and the two identities are equal or differ only in a checksum binding that one of
  them lacks
- **THEN** admission answers with the recorded identity and says that the set holds it
- **AND** the transition completes and returns that identity
- **AND** the version keeps its one release Attestation, so a checksum file presented after a
  record without the binding is checked and not recorded.

#### Scenario: The set returns another record than the admitted identity

- **WHEN** the Attestation set answers a transition with a record that is not the identity
  its admission named, as when another writer recorded the version in between
- **THEN** the transition refuses with `identity_transition_attestation_mismatch`
- **AND** it returns no identity that it did not record.

#### Scenario: The wheel changes while it is accepted

- **WHEN** the wheel's bytes change after the transition read them
- **THEN** the package store receives the bytes whose digest was admitted
- **AND** no file is stored under a digest that is not its own.

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

ETHOS SHALL project one accepted product-release version to public channels and its matching signed
tag. Published artifacts SHALL be immutable. Development build identities SHALL remain exact local
selections, not automatic channel upgrade versions. Pre-release and stable delivery SHALL remain
distinct. A published file that disagrees with the release's checksum file SHALL refuse the
acceptance that channels consume. The product's release tag SHALL NOT publish under a release
policy gap.

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

- **WHEN** a hosted runner without the repository proof builds or qualifies release bytes outside
  a rehearsal
- **THEN** only the trusted signed tag of that exact clean source, its committed version and
  curated entry admit the release identity
- **AND** an unsigned, untrusted, misplaced or mismatched tag is refused before any build effect
- **AND** publication carries only the wheels and archives whose qualification evidence
  matches their bytes

#### Scenario: Selected package bytes change during qualification

- **WHEN** a selected wheel is missing, redirected or differs from its bound bytes or build
- **THEN** qualification rejects it before effects or before producing passing evidence
- **AND** pre-execution rejection preserves existing work and unrelated development evidence

#### Scenario: A published file disagrees with the checksum file

- **WHEN** a release is accepted with its checksum file, and a published wheel or archive that the
  acceptance read differs from its line in that file or has none
- **THEN** the acceptance refuses with `accepted_release_checksum_mismatch:<file name>`
- **AND** the refusal precedes every effect, so no package, Attestation or channel projection
  changes.

#### Scenario: A checksum file is malformed or omits the accepted wheel

- **WHEN** the checksum file is not one `<digest>  <name>` line per file name, or lists no wheel or
  archive with the accepted wheel's digest
- **THEN** the acceptance refuses with `accepted_release_checksums_invalid` or
  `accepted_release_artifacts_invalid`
- **AND** no identity binds that file.

#### Scenario: The product's release tag is published under a release policy gap

- **WHEN** `ethos publish` targets a release tag in the repository that declares the ETHOS product
  profile while the release policy report of its checkout holds a required gap
- **THEN** the result blocks with that gap among its required gaps
- **AND** its data carries the report under `release_policy`
- **AND** its next step names the repair of the first report that has one.

#### Scenario: A governed repository publishes a release tag

- **WHEN** `ethos publish` targets a release tag in a repository that does not declare the ETHOS
  product profile
- **THEN** the publication reads no product release policy
- **AND** its role policy, topology and proof decide as before.

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
  with its rollback from each predecessor that a beta's journey requires, and
  uninstall
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

### Requirement: Windows runtime archives fit the Windows path limit

A release archive SHALL name its runtime directory with the first 16 hexadecimal digits of the
runtime digest, so that its Windows interpreter path stays within 64 characters. An archive carrier
SHALL resolve that prefix to the full digest from the runtime manifest and SHALL refuse a directory
that is not its prefix. The host store and its selectors SHALL keep the full digest.

#### Scenario: A deep install root runs the interpreter

- **WHEN** a Windows host installs the archive under a 157-character install root
- **THEN** the interpreter path is 205 characters and Windows starts the interpreter.

#### Scenario: The archive layout outgrows the budget

- **WHEN** the release builder lays out a Windows archive whose interpreter path inside the archive
  exceeds 64 characters
- **THEN** the distribution tests fail before a release is built.

#### Scenario: An archive directory names another runtime

- **WHEN** an archive's runtime directory is not a prefix of the digest its manifest records
- **THEN** runtime selection refuses the archive before any effect.

### Requirement: Published release artifacts carry build provenance

The release publication SHALL attest every archive and wheel it publishes, and the checksum file
that lists them, with a GitHub artifact attestation of its own workflow run before it creates the
release, so that no release exists without them and a consumer can verify each published file's
origin independently of ETHOS.

#### Scenario: A release is published

- **WHEN** the release run publishes the qualified archives and wheels of a signed tag
- **THEN** each of those files has a GitHub artifact attestation of that run
- **AND** the attestation runs before the release is created, so a failed attestation stops the
  publication

#### Scenario: Release provenance and ETHOS proof stay separate

- **WHEN** a consumer verifies a published archive with `gh attestation verify`
- **THEN** the result establishes the file's build origin only
- **AND** it neither replaces an ETHOS proof or release Attestation nor is replaced by one

#### Scenario: A release publishes its checksum file

- **WHEN** the release run has assembled `SHA256SUMS` beside the qualified archives and wheels
- **THEN** `SHA256SUMS` has a GitHub artifact attestation of that run, made in the same step as
  theirs
- **AND** a failed attestation stops the publication before the release is created.

### Requirement: A hosted journey qualifies each published prerelease

After a release run publishes a prerelease, a hosted journey SHALL install it through the exact
GitHub pin, with provenance verification, on macOS and Linux. From the archives that this
acquisition verified it SHALL then pass, in fixture adopters on fresh host stores, a cold install,
host-store pinning, hook binding, a full proof and status, an upgrade from each predecessor with
its rollback, and uninstall. A dispatch SHALL run the journey alone for an already published
prerelease.

#### Scenario: A prerelease is published

- **WHEN** a release run publishes a prerelease
- **THEN** the journey runs on macOS and Linux against its published assets
- **AND** each leg's receipt names the result of every journey step.

#### Scenario: A published prerelease is qualified again

- **WHEN** a dispatch names an already published prerelease for the journey alone
- **THEN** only the journey runs, and the release is not published again.

#### Scenario: Each leg installs through the pin

- **WHEN** a leg acquires the prerelease or one of its predecessors
- **THEN** it locks the exact GitHub pin of that release and installs its own platform from the lock
- **AND** its receipt names the Mise release, each release's class and each lock's format version.

#### Scenario: The steps run on the acquired archives

- **WHEN** a leg runs the cold install, an upgrade or the uninstall
- **THEN** the release it installs is the archive that acquisition verified, installed offline
- **AND** the installation that the pin made is not the one the steps run on.

### Requirement: The journey installs only verified release bytes

The journey SHALL check each archive it installs against its release's checksums and, by its
release's class, against its build attestation's signer workflow, source ref and source commit,
before installing it. Without named predecessors, the previous release SHALL be the first earlier
changelog entry whose release the forge published; the receipt SHALL name each entry it skipped.
Each leg SHALL upload its receipt and stage events whether it passes or fails.

#### Scenario: A published archive does not match its release

- **WHEN** a downloaded archive's digest differs from its release checksums, or the prerelease's
  archive fails attestation verification
- **THEN** the journey fails before it installs that archive
- **AND** the leg still uploads its receipt and stage events.

#### Scenario: An earlier version was tagged but never published

- **WHEN** the changelog entry after the prerelease names a version that has no published release
- **THEN** the journey upgrades from the next earlier version whose release exists
- **AND** its receipt names the skipped version.

#### Scenario: An attestation names another source

- **WHEN** an `attested-main` release's attestation names another signer workflow, a ref other than
  `main`, or a commit other than the one its tag names
- **THEN** the journey fails before it installs that release's archive.

#### Scenario: A checksum-class release is installed

- **WHEN** a predecessor's class is `checksum`
- **THEN** the journey checks its archive against its release's checksums only
- **AND** its receipt names that class.

### Requirement: A beta's journey starts from every release that adopters select

A beta's journey evidence SHALL include an upgrade, with its rollback, from the previous release
and from every release that a subject pins or has selected. A subject is a governed repository
that the releasing host can read, that has selected a runtime of the product, and whose last
landed bump is inside the support window: at most 14 days before the newest landed bump read.
Release preparation SHALL derive those releases from the subjects' own trees and SHALL record no
count of subjects.

#### Scenario: A governed adopter selects an older release

- **WHEN** a subject inside the support window still pins or has selected a published release
  older than the previous release
- **THEN** a beta's journey evidence includes an upgrade from that release with its rollback
- **AND** without that evidence, the beta is not qualified for that subject.

#### Scenario: A subject falls outside the support window

- **WHEN** a subject's last landed bump is more than 14 days older than the newest landed bump
  among the subjects read
- **THEN** the releases that only it names are not derived
- **AND** the subject is reported as outside the window.

#### Scenario: Time alone moves no subject

- **WHEN** no subject lands a bump for longer than 14 days
- **THEN** every subject that was inside the support window stays inside it.

#### Scenario: A bump is read from the accepted branch

- **WHEN** a subject's accepted branch changed its pinned release and later changed its Mise
  configuration without moving the pin
- **THEN** its last landed bump is the commit that changed the pinned release
- **AND** a change of the pin's form that keeps the release is no bump.

#### Scenario: A subject declares no pin

- **WHEN** a recorded repository's accepted branch declares no pin, and the repository has
  selected a runtime
- **THEN** it is a subject by its selection, and the release it has selected is derived
- **AND** its last landed bump has no time, so it is inside the support window and the result
  gives its time as unknown.

#### Scenario: A subject's declared pin cannot be read

- **WHEN** a recorded repository's accepted branch declares a pin that cannot be read, such as
  two keys, a version prefix or text that is not TOML, and the repository has selected a runtime
- **THEN** it is a subject by its selection, inside the support window, and that pin names no
  release
- **AND** the result counts such pins by themselves, apart from the consumers that could not be
  read.

#### Scenario: A subject pins one release and has selected another

- **WHEN** a subject's accepted branch pins one release and the subject has selected another
- **THEN** both releases are derived, and the result shows the pin and the selection.

#### Scenario: A repository that cannot be read is no subject

- **WHEN** a recorded repository is gone, its record or its accepted branch cannot be read, or it
  neither pins a release nor has a selection that can be read
- **THEN** it is no subject, and the derivation refuses nothing for it
- **AND** the result counts the repositories and records that could not be read, each record
  once.

#### Scenario: A subject's selection cannot be read

- **WHEN** a recorded repository's accepted branch pins a release, and its selector cannot be
  read
- **THEN** it is a subject by its pin, and that selection names no release
- **AND** the result counts such selections by themselves, apart from the consumers that could
  not be read.

#### Scenario: A subject is frozen on its runtime

- **WHEN** a subject's owner froze it on a runtime, so that it takes no release
- **THEN** its recorded waiver names the subject's shape and its runtime, and no repository
- **AND** the condition that every subject is bumped does not count it
- **AND** its release stays a predecessor while its last landed bump is inside the support window.

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

### Requirement: A published runtime archive declares what it ships

Each hosted release SHALL publish two inventories for every runtime archive: an SPDX 2.3 SBOM and a Syft JSON inventory with Go symbols, each naming the archive's published file and SHA-256 and listing its components. Publication SHALL refuse any archive whose inventories name another digest or file or are declared twice, refuse a required archive without both, leave out and name an optional archive without both, and attest them.

#### Scenario: An archive's inventories match its bytes

- **WHEN** a release leg's inventories name its archive's published name and digest and list its expected components
- **THEN** the release publishes both beside the archive, covered by `SHA256SUMS` and the build provenance attestation

#### Scenario: An optional archive's declaration is incomplete

- **WHEN** an optional release leg uploads only one of its two inventories
- **THEN** that archive is not published
- **AND** the release notes and the assembler's output name its host

#### Scenario: A binding does not match

- **WHEN** any release leg's inventory names another digest or file, or a second declaration sits beside the two
- **THEN** assembly fails with `release_assets_inventory_mismatch:<host>`, for an optional host too

#### Scenario: A one-package SBOM

- **WHEN** an inventory lists only the archive itself
- **THEN** assembly fails with `release_assets_inventory_components_missing:<host>`

#### Scenario: An expected component is missing

- **WHEN** the catalog lacks the locked `uv` crate, a declared Go tool's module or a shipped Python
  distribution
- **THEN** the inventory owner refuses and names the missing component

#### Scenario: The catalog misses a locked executable

- **WHEN** the catalog lacks the shipped Node executable, and its SHA-256 equals the executable of
  the locked Node supply on that host
- **THEN** both inventories list Node at the locked version, bound to that digest and marked as
  declared from the locked supply
- **AND** the binary scan no longer reports that file as an unidentified executable
- **AND** the supply-chain evidence lists Node apart from the cataloged components

#### Scenario: A declared executable differs from its supply

- **WHEN** the catalog lacks the shipped Node executable, and its SHA-256 differs from the locked
  supply's for the archive's runtime platform
- **THEN** the inventory owner refuses with `release_inventory_component_unverified:node`

#### Scenario: The catalog finds the executable itself

- **WHEN** the catalog already lists Node at the shipped path
- **THEN** the inventory owner declares nothing for it

### Requirement: A release run reports the binary-level advisories of what it shipped

After publication, and on demand for a published release, a read-only hosted job SHALL check each Syft inventory against `SHA256SUMS` and its archive, and scan it with the pinned Grype. Its report SHALL name the scanner, the database's build time, source and checksum, each archive's digest, one row per archive, package, version and advisory, and unidentified executables. The scan SHALL NOT block the release.

#### Scenario: A release run scans what it shipped

- **WHEN** a hosted release run has published its archives and inventories
- **THEN** its report lists each archive's digest and the advisories that Grype matched in its inventory
- **AND** the release itself does not wait for the report

#### Scenario: A published release is scanned again

- **WHEN** a `scan_tag` dispatch names an already published release
- **THEN** only the scan job runs, over that release's published inventories
- **AND** its report records the database that produced it

#### Scenario: An inventory is missing

- **WHEN** a host's archive is published without its Syft inventory
- **THEN** the report names that host as not scanned
- **AND** never reports zero findings for it

### Requirement: A release names each declared platform that it does not publish

The release legs SHALL be declared once, each as required or optional, and the release workflow and
its assembler SHALL read that declaration. Publication SHALL refuse a missing required platform and
an artifact for an undeclared platform. A declared optional platform that a release does not publish
SHALL be named, with its cause, in the assembler's output and in the release notes, with the rule
that an adopter installing ETHOS on it keeps its current release.

#### Scenario: An optional leg fails before it uploads

- **WHEN** a declared optional release leg fails before it uploads its artifact
- **THEN** the release publishes the other platforms
- **AND** `left-out.json` names that platform with the cause `leg_incomplete`
- **AND** the release notes name it and state the adopter rule

#### Scenario: A required leg publishes nothing

- **WHEN** a declared required release leg uploads no admitted archive
- **THEN** assembly fails with `release_assets_platform_missing:<host>`

#### Scenario: An artifact names an undeclared platform

- **WHEN** an uploaded artifact names a platform that no release leg declares
- **THEN** assembly fails with `release_assets_host_undeclared:<host>`

#### Scenario: The workflow tolerates only optional failures

- **WHEN** the release workflow is projected from the declared legs
- **THEN** only the optional legs may fail without failing the run
- **AND** the assembler receives exactly the declared required and optional platforms

### Requirement: Release platforms catalog their archives on every hosted commit run

On every hosted commit run, each host-conformance leg whose runner and Python match a declared
release leg SHALL catalog the runtime archive that its install smoke kept, with the release's
inventory owner and its checks. A release platform's inventory step SHALL NOT first run when a
release is published.

#### Scenario: A commit's Windows leg catalogs its archive

- **WHEN** a hosted commit run's Windows host-conformance leg on the release Python keeps its
  runtime archive
- **THEN** that leg catalogs the archive and checks its expected components

#### Scenario: A release leg changes its runner

- **WHEN** a declared release leg moves to another runner or Python
- **THEN** the host-conformance legs that catalog their archives follow that declaration

#### Scenario: A component is missing on a commit

- **WHEN** a host-conformance leg's inventory lacks an expected component that no locked supply can
  declare
- **THEN** that commit's hosted run fails with the missing component named

### Requirement: Release assembly admits only the tagged commit's bytes

Release assembly SHALL admit a platform upload only when its smoke record names the release head as
its source commit and the tag's version, in its distribution form, as its distribution version. Any
other upload SHALL refuse the release, naming its host.

#### Scenario: Every leg was built from the tagged commit

- **WHEN** every uploaded leg records the release head and the tag's distribution version
- **THEN** assembly admits the legs as before

#### Scenario: A leg was built from another commit

- **WHEN** an uploaded leg records a source commit other than the release head
- **THEN** assembly fails with `release_assets_identity_mismatch:<host>`

#### Scenario: A leg carries another version

- **WHEN** an uploaded leg records a distribution version other than the tag's
- **THEN** assembly fails with `release_assets_identity_mismatch:<host>`

### Requirement: Root Node manifests stay unpublishable

The root `package.json`, which declares the repository's JavaScript tools, SHALL stay private when
it declares workspaces and SHALL carry no person attribution metadata, so no Node manifest can
publish product assets.

#### Scenario: A root package declares workspaces

- **WHEN** `ethos prove --gate product-boundary --json` audits the root `package.json`
- **THEN** a root package that declares workspaces without `private: true` is reported
- **AND** author, authors, maintainers, and contributors metadata are absent

### Requirement: A release installs through one exact GitHub pin

A published release SHALL install through one Mise entry, `"github:HengYangDS/ethos" = "<version>"`
under `[tools]`, with `locked_verify_provenance = true` under `[settings]` and no other option for
that tool. Each release SHALL have one class, `attested`, `attested-main` or `checksum`, naming what
its bytes are verified against. No installation claim SHALL exceed what its verifier checked, and a
lock's provenance field alone SHALL prove nothing.

#### Scenario: The pin locks and installs a release dispatched from main

- **WHEN** the journey locks the pin of an `attested-main` release for every platform the release
  published and installs its own platform, both with the CI's bound Mise
- **THEN** each lock entry SHALL name that release's own archive, the digest its `SHA256SUMS` lists
  and `github-attestations`
- **AND** the install SHALL hold the console in `bin/` and one runtime in `runtime/<16 hex>`

#### Scenario: A lock in an earlier format is relocked in place

- **WHEN** the pin is locked into an existing lock of format version 3
- **THEN** the lock SHALL keep its format version and record `github-attestations` for the pin

#### Scenario: A release's class follows its dispatch

- **WHEN** a release was dispatched from `main` and its attestation's source commit is the commit
  its signed tag names
- **THEN** its class SHALL be `attested-main`
- **AND** a release dispatched from its tag ref SHALL be `attested`
- **AND** a release without attestations, or whose attestation names another commit, SHALL be
  `checksum`

#### Scenario: Changed bytes are refused at install

- **WHEN** the bytes behind a locked entry of the pin do not match that entry's checksum
- **THEN** the locked install SHALL refuse them

#### Scenario: Another repository's attestation is refused

- **WHEN** a lock entry of the pin names bytes that only another repository attested
- **THEN** the locked install SHALL refuse them, or the lock SHALL record no `github-attestations`

#### Scenario: A refusal that does not hold keeps every claim at checksum

- **WHEN** either refusal does not hold under a Mise release
- **THEN** the journey SHALL fail and its receipt SHALL name that refusal
- **AND** no installation under that Mise release SHALL be described as more than checksum-verified

#### Scenario: A local archive installs in the same layout

- **WHEN** the local install smoke installs its own archive offline from a `file://` table
- **THEN** the install SHALL hold the console in `bin/` and one runtime in `runtime/<16 hex>`

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

### Requirement: A release records what it upgrades from

The release binding SHALL record under `[release.upgrade_from]` each release that the release
upgrades from, with its class, and SHALL name no repository there. `ethos lane upgrade-from` SHALL
derive that set offline for the committed release, report each subject's accepted head, pin,
selection and last bump without its path, count the subjects, and block when the record is
empty, lacks a derived release, or gives a release another class than its own.

#### Scenario: The record lists every derived release

- **WHEN** the committed binding records every release that the operation derives, each with its
  class
- **THEN** the operation passes and names no next action
- **AND** a recorded release that no subject names does not block.

#### Scenario: The record is absent or empty

- **WHEN** the committed binding declares no `[release.upgrade_from]`, or an empty one
- **THEN** the operation blocks with `release_upgrade_from_empty`
- **AND** its result still carries the derived releases with their classes.

#### Scenario: The record lacks a derived release

- **WHEN** a subject inside the support window pins or has selected a release that the record does
  not list
- **THEN** the operation blocks with `release_upgrade_from_incomplete:<releases>`, newest first.

#### Scenario: A recorded class is not the release's class

- **WHEN** the record names something other than one exact release, or gives a release a class
  other than the one its dispatch has
- **THEN** the operation blocks with `release_upgrade_from_invalid`
- **AND** its result still carries the derived releases with their classes.

#### Scenario: A subject selects a build that is no listed release

- **WHEN** a subject inside the support window pins or has selected a version that the changelog
  does not list, such as a development build
- **THEN** that version is no predecessor, and the operation refuses nothing for it
- **AND** the result names the version with the count of subjects that name it.

#### Scenario: The result counts the subjects

- **WHEN** the operation reads subjects inside the support window
- **THEN** its result states how many of them pin in each form, how many are subjects by their
  selection alone, how many recorded consumers and records could not be read, and how many
  installations record no consumer
- **AND** for the release itself and for each predecessor, how many subjects name it by their
  pin and how many by their selection alone, each subject once for a release.

#### Scenario: The changelog's history is invalid

- **WHEN** the releasing repository's changelog lists its releases out of order or names one
  twice
- **THEN** the operation blocks with the history's own errors and derives nothing.

#### Scenario: A refusal names its own repair

- **WHEN** the operation blocks for a gap that is not one of the record's
- **THEN** its next action does not ask for the record
- **AND** an operating system error is `release_upgrade_from_store_unreadable` with the error's
  name, and the result carries no path.

#### Scenario: The host records no consumer

- **WHEN** the host has no store of installations
- **THEN** the operation derives the previous release alone and reports no subject.

#### Scenario: The operation is a read

- **WHEN** `ethos lane upgrade-from --json` runs
- **THEN** it selects `lane.upgrade-from`, whose only effect is `read`, and exits 0 on every verdict
- **AND** its rows come newest bump first and carry no repository's name or path.

### Requirement: The releasing host accepts the release that it installed

The releasing host SHALL accept, once, the release that its invoked installation is.

#### Scenario: The releasing host accepts the release it installed

- **WHEN** `ethos release accept --checksums <SHA256SUMS> --apply` runs in the product repository
  through an installed release build of the version that the accepted branch commits, built from
  the commit that the version's tag names
- **THEN** the transition stores the installed wheel and records the identity bound to the
  checksum file
- **AND** the same request without `--apply` writes nothing and names that apply as its next step.

#### Scenario: An accepted release is accepted again

- **WHEN** the request runs after the version's identity is recorded, with the checksum binding
  or without it
- **THEN** the result's state is `unchanged`, on a preview and on an apply, and its data carries
  the recorded identity
- **AND** neither the package store nor the Attestation set changes.

#### Scenario: The apply cannot write the store or the set

- **WHEN** the apply meets an operating system error after its inputs were read
- **THEN** it refuses with `release_acceptance_store_unavailable:<error name>`
- **AND** the refusal's repair names the Git common directory, not the checksum file.

#### Scenario: The invoked installation is not the release to accept

- **WHEN** the invoking `ethos` is a source checkout or a development build, or an installed
  release older or newer than the version that the accepted branch commits
- **THEN** the acceptance refuses with `release_installation_absent`,
  `release_installation_older:<version>` or `release_installation_newer:<version>`
- **AND** the refusal precedes every effect and names its repair
- **AND** the two versions are ordered as SemVer texts, so a committed version outside the
  wheel profile reads as older or newer.

#### Scenario: The release has no tag, or the installation has another source

- **WHEN** the repository holds no tag of the version that the accepted branch commits, or the
  installed wheel was not built from the commit that the tag names
- **THEN** the acceptance refuses with `release_tag_missing:v<version>` or
  `release_wheel_build_identity_stale`
- **AND** no package or Attestation changes.

#### Scenario: A release is accepted outside the product repository

- **WHEN** the command runs in a repository that does not declare the ETHOS product profile
- **THEN** it refuses with `release_acceptance_product_only`
- **AND** that repository records no release identity
- **AND** a profile that cannot be read refuses with `repository_profile_invalid:<path>`, never
  as another repository.

### Requirement: One owner gives every journey child a fresh environment

One environment owner SHALL give every child process of the release journey a new home and
temporary directory, Git without system or global configuration, system attributes or templates,
and a path of one link for each declared executable. No agent socket, desktop variable or other
host variable SHALL reach a child, except the forge token and the tool supply's location in
acquisition, as the scenarios bound them. The journey SHALL run the Mise executable whose digest
the repository binds.

#### Scenario: A child inherits or is handed its environment

- **WHEN** a journey stage starts a child that inherits the stage's environment, or one that is
  handed it
- **THEN** the child SHALL see the stage's own home, temporary directory, Git configuration file
  and template directory, all new and empty
- **AND** its path SHALL resolve the declared executables and no other

#### Scenario: The host holds credentials and a desktop session

- **WHEN** the host's environment holds an agent socket, a forge token or a desktop variable
- **THEN** no stage's process SHALL hold any of them, and no child SHALL inherit one
- **AND** acquisition SHALL hand the forge token to the forge's client and to Mise's lock and
  install of a pin, and to no other child

#### Scenario: Acquisition finds the host's tool supply

- **WHEN** the host's environment says where its tool supply is
- **THEN** acquisition's own process SHALL hold those variables only while it prepares Mise from
  that supply
- **AND** no child that starts after that preparation SHALL receive them, whether it inherits
  its environment or is handed it
- **AND** qualification's process SHALL NOT hold them

#### Scenario: The host installed another Mise

- **WHEN** the host's path holds a Mise executable
- **THEN** the journey SHALL run the executable of the repository's tool supply, whose digest the
  repository binds, and not the host's

#### Scenario: A fixture adopter is built

- **WHEN** the journey creates a fixture adopter and its signed commits
- **THEN** each of those Git commands SHALL run in the stage's environment

#### Scenario: A stage ends

- **WHEN** a stage ends, passing or not
- **THEN** the journey's own process SHALL hold the host's environment again

#### Scenario: A Windows host runs a stage

- **WHEN** a stage runs on Windows
- **THEN** its children SHALL receive the Git variables over the install smoke's minimal
  environment, and the home, temporary directory and path SHALL stay the host's
- **AND** a stage whose declared executable that path does not hold SHALL refuse at its start

### Requirement: Acquisition is the journey's only networked stage

The release journey SHALL run as two stages. Acquisition, the only stage that reaches the network,
SHALL verify the prerelease and each predecessor, prove each release's exact GitHub pin, and write
a manifest of the archives it verified. Qualification SHALL read that manifest alone, check its
environment before it starts a child, hash each archive again before it installs it offline, and
run every journey step. Each leg's receipt SHALL name its venue.

#### Scenario: Acquisition completes

- **WHEN** acquisition has verified each release by its class and Mise has locked, installed and
  refused the rebound locks of the prerelease's pin
- **THEN** it SHALL write a manifest that names, the prerelease first, each release's version,
  class, archive and SHA-256
- **AND** it SHALL remove what the pins installed

#### Scenario: Qualification's environment shows more than was declared

- **WHEN** qualification's environment holds a variable that was not declared, lacks or changes a
  declared one, holds a home, temporary directory, template directory or Git configuration that
  is not empty, or holds a path entry that is not one link to an existing declared executable
- **THEN** the leg SHALL fail with `journey_environment_not_hermetic:<what>` before its first
  child

#### Scenario: An archive changed after acquisition

- **WHEN** an archive's SHA-256 differs from the one its manifest entry records
- **THEN** the leg SHALL fail with `release_journey_archive_tampered:<archive>` before Mise
  installs it
- **AND** Mise SHALL be given the manifest's SHA-256 as the archive's checksum, so that it
  refuses bytes that change after that check

#### Scenario: The manifest is not whole

- **WHEN** the manifest is absent, unparsable or empty, an entry lacks a field or adds one, or an
  archive lies outside the manifest's directory
- **THEN** the leg SHALL fail with `release_journey_manifest_invalid` before any install

#### Scenario: Qualification installs a release

- **WHEN** qualification installs the prerelease or a predecessor
- **THEN** Mise SHALL install the acquired archive in offline mode from a local table, in the
  layout that the pin installs

#### Scenario: A leg records where it ran

- **WHEN** a leg writes its receipt
- **THEN** `venue` SHALL read `ci` under a CI runner and `local` otherwise

### Requirement: A release head is rehearsed on hosted runners before its tag

The hosted workflow SHALL offer a dispatch that names one commit. At that commit alone it SHALL
build and qualify the release wheel on every declared release platform, assemble the release's
assets and run the adopter journey on each declared host, before a tag of that version exists. A
rehearsal job SHALL hold no permission to publish or attest, and one job SHALL give the
rehearsal's verdict.

#### Scenario: A dispatch names the head of its ref

- **WHEN** a dispatch names the commit that is the head of its ref
- **THEN** the run qualifies that commit as a batch-head dispatch does
- **AND** it builds every declared release platform, assembles the assets and runs the journey
- **AND** nothing is attested, published or tagged.

#### Scenario: A dispatch names another commit

- **WHEN** a dispatch names a commit that is not the head of its ref
- **THEN** no rehearsal job builds, assembles or installs anything
- **AND** the rehearsal's verdict job fails.

#### Scenario: A dispatch also names a release, a journey, a scan or the supply image

- **WHEN** a dispatch names a head to rehearse and one of the workflow's other selecting inputs
- **THEN** no rehearsal job builds, assembles or installs anything
- **AND** the rehearsal's verdict job fails.

#### Scenario: A required leg fails

- **WHEN** a required platform's leg, the assembly or a declared host's journey fails
- **THEN** the rehearsal's verdict job fails
- **AND** a failed optional platform is named among the platforms left out and fails nothing.

### Requirement: A rehearsal build carries release identity before the tag

A rehearsal build SHALL carry release identity only when its checkout is clean at the named
commit, that commit's signature passes the bound commit trust, its committed version has no tag
and its changelog entry passes the release tag policy. Outside a rehearsal, a hosted release
build SHALL still be admitted by its signed tag alone. A rehearsal SHALL accept, attest and
publish nothing.

#### Scenario: The version already has a tag

- **WHEN** a rehearsal build names a head whose committed version has a tag
- **THEN** the build refuses with `release_rehearsal_tag_exists:v<version>` before any build
  effect.

#### Scenario: The head's signature is not trusted

- **WHEN** the bound commit trust does not pass the signature of the named head
- **THEN** the build refuses with `release_rehearsal_head_untrusted` before any build effect.

#### Scenario: A rehearsal request names a tag

- **WHEN** a build request carries both the rehearsal mark and a tag
- **THEN** it is refused as an invalid release request.

### Requirement: A rehearsal's journey installs the run's own assembly

A rehearsal's journey SHALL install the candidate offline from its platform's archive of the same
run, admitted only when its digest is the one that the run's checksum file lists, and SHALL
acquire each predecessor through its exact pin. Its predecessors SHALL be the releases that the
release binding records at the head, or the previous published release when it records none.

#### Scenario: The archive is not the assembled one

- **WHEN** the archive's digest differs from the checksum file's line for its published name
- **THEN** the journey fails before it installs the archive
- **AND** the leg still uploads its receipt and stage events.

#### Scenario: The head records its predecessors

- **WHEN** the release binding at the head records releases under `[release.upgrade_from]`
- **THEN** the journey upgrades from each of them, and rolls back to it, in its own host store
- **AND** its receipt names the record as the source of the set.

#### Scenario: The head records no predecessor

- **WHEN** the release binding at the head records no release
- **THEN** the journey upgrades from the first earlier changelog entry whose release the forge
  published
- **AND** its receipt names the changelog as the source of the set.

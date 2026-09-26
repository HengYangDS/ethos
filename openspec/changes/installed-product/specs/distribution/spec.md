## ADDED Requirements

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
SHALL prevent deletion without erasing successful activation evidence.

#### Scenario: Upgrade is interrupted

- **WHEN** preparation or activation fails between durable effect and acknowledgement
- **THEN** recovery identifies the selected version and preserves the previous usable version
- **AND** it does not repeat a destructive effect from missing acknowledgement alone

#### Scenario: A live repository still references an old installation

- **WHEN** uninstall or reclamation finds a live version consumer
- **THEN** the consumer's selected bytes remain available
- **AND** cleanup reports the exact remaining dependency

#### Scenario: A retained adopter uses the previous complete branch-role schema

- **WHEN** an incumbent accepted commit has every previously required branch-role field but no `canonical_sibling_worktrees` field
- **THEN** accepted closeout and Lease reacquisition interpret that historical absence as `false`
- **AND** current policy validation still rejects every other incomplete or unknown branch-role table
- **AND** neither operation rewrites the incumbent commit or retained Work Lane content

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
source, including valid, denied and unknown outcomes, repository isolation,
upgrade, rollback and exit. A wheel build, import or source-only test SHALL NOT
be reported as complete installed-product acceptance.

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

### Requirement: Homebrew is a delivered installation channel

ETHOS SHALL support native Homebrew installation outside its source checkout.
Package-manager ownership, product identity, repository selection and project
toolchain SHALL remain distinct. Homebrew delivery SHALL NOT require one
particular freezing tool or silently select a different repository runtime.

#### Scenario: A clean host installs the published product

- **WHEN** Homebrew installs the published ETHOS package
- **THEN** installed CLI and MCP work without an ETHOS checkout or development environment
- **AND** version-matched guidance and required product supply are discoverable

#### Scenario: Package upgrade and uninstall preserve repository ownership

- **WHEN** Homebrew upgrades or removes its owned package
- **THEN** selected repository identities and user-authored content are not silently changed
- **AND** live-use and recovery boundaries are verified rather than inferred from formula existence

### Requirement: Platform support is established by native delivered behavior

ETHOS SHALL deliver native macOS and Linux support on explicitly declared
architecture and OS baselines. Windows support SHOULD be provided when qualified.
Required-platform delivery SHALL NOT depend on an unqualified Windows path.

#### Scenario: A release advertises supported platforms

- **WHEN** a platform is included in the release support declaration
- **THEN** its delivered artifact passes native installation, CLI/MCP, hooks, upgrade and exit
- **AND** unsupported combinations remain explicit rather than inheriting another platform's proof

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
- **AND** native signing precedes payload sealing and exact installed acceptance
- **AND** the release, signed tag and channel projections identify the same frozen source

#### Scenario: A release candidate is selected for installation qualification

- **WHEN** explicit release arguments select exact accepted-source candidate bytes
- **THEN** the existing offline installation workload verifies those bytes without substitution
- **AND** its separate receipt binds build identity and preserves default development evidence
- **AND** qualification does not accept, notarize or publish the release

#### Scenario: Selected package bytes change during qualification

- **WHEN** a selected wheel is missing, redirected or differs from its bound bytes or build
- **THEN** qualification rejects it before effects or before producing passing evidence
- **AND** pre-execution rejection preserves existing work and unrelated development evidence

#### Scenario: A newer published version is selected

- **WHEN** a channel offers a subsequent accepted release
- **THEN** the target package manager orders it after the prior release
- **AND** a pre-release does not replace a stable installation without explicit selection

### Requirement: Credential access does not authorize a product release

ETHOS SHALL admit each signing request against its project, source, version,
target, publisher, identifiers, entitlements and exact candidate bytes.
Operator-owned credentials MAY serve multiple projects within an authorized
execution boundary. Their availability or profile name SHALL NOT grant release
authority or transfer another project's acceptance.

#### Scenario: Two projects share a publisher

- **WHEN** independent projects use the same authorized publisher identity
- **THEN** each signs only its admitted candidate through the existing release owner
- **AND** temporary resources, submission IDs, evidence and publication targets remain distinct
- **AND** neither project can satisfy its acceptance with the other's successful submission

#### Scenario: An unauthorized or altered candidate reaches the signer

- **WHEN** a request changes the admitted project, publisher, target, identifiers, entitlements or bytes
- **THEN** signing is rejected before credential-backed effects
- **AND** previous accepted artifacts and the other project's state remain unchanged

#### Scenario: The signing execution boundary is not established

- **WHEN** untrusted build code can invoke the signer or select its executable commands
- **THEN** release qualification reports the missing execution boundary
- **AND** profile naming, shared-user ACLs and CI environment labels do not establish isolation
- **AND** secret-free construction and unrelated verification may continue

#### Scenario: Native signing is performed in a credential-capable environment

- **WHEN** an admitted native candidate is prepared for signing and sealing
- **THEN** the signer modifies only an exclusively owned disposable copy
- **AND** the existing runtime owner binds the transformed payload to a new identity
- **AND** structural checks do not execute candidate interpreters, plugins or build commands
- **AND** final executable qualification occurs in a separate credential-free target

#### Scenario: macOS release media is prepared

- **WHEN** a native macOS candidate is delivered outside the App Store
- **THEN** its release envelope supports native notarization and stapled ticket delivery
- **AND** submitted and final envelope identities remain bound to the same sealed inner runtime
- **AND** a portable archive or ad-hoc signature alone does not establish release qualification

#### Scenario: Native media construction fails

- **WHEN** the selected native image producer fails or exceeds its bounded execution time
- **THEN** construction preserves the previous output and removes its owned temporary payload
- **AND** it does not retry creation with a different producer or weaken payload identity checks
- **AND** carrier construction alone does not authorize signing, acceptance or publication

### Requirement: Credential transitions preserve exact release evidence

ETHOS SHALL distinguish code-signing identity, notarization authentication,
submission result, installation and publication. Each signing or packaging
transformation SHALL bind its input and output bytes. Credential transitions
SHALL use the operator's existing native store without secret copies in projects.

#### Scenario: Notarization acknowledgement is lost

- **WHEN** a bounded submission attempt ends without a known result
- **THEN** the operation retains UNKNOWN and reconciles its exact submission when identifiable
- **AND** team-wide history or another project's result does not authorize a repeated upload

#### Scenario: A shared credential is replaced

- **WHEN** an operator migrates or rotates a shared credential
- **THEN** each known consumer verifies its replacement before routine retirement of old access
- **AND** provider revocation, local-profile deletion and recovery-material retirement remain separate effects
- **AND** compromise follows immediate revocation and recovery rather than routine overlap

### Requirement: Curated release notes follow Keep a Changelog

ETHOS SHALL follow Keep a Changelog 1.1.0 for user-facing release notes.
Release preparation SHALL verify an exact-version entry with a real release
date, applicable change categories and verifiable history links. Upcoming
changes SHALL remain under Unreleased until selected for explicit release;
commit dumps SHALL NOT substitute for curated compatibility information.

#### Scenario: A release is prepared from Unreleased changes

- **WHEN** an exact accepted source is selected for explicit release
- **THEN** its version entry uses YYYY-MM-DD and meaningful Added, Changed, Deprecated, Removed, Fixed or Security sections
- **AND** missing, duplicate, mismatched or malformed target entries block that release
- **AND** ordinary source acceptance may retain Unreleased notes without claiming publication

#### Scenario: Historical release evidence is unavailable

- **WHEN** an earlier entry lacks a verifiable tag or publication record
- **THEN** the uncertainty remains explicit and historical content is preserved
- **AND** no tag, date or release claim is invented to make the changelog appear complete

## MODIFIED Requirements

### Requirement: Product version has one repository authority

ETHOS SHALL derive product-release projections from one tracked SemVer 2.0.0
target. Unpublished source iterations MAY share it. Public CLI, SDK, MCP,
configuration and persisted-state compatibility SHALL determine increments.
Once an explicit release identity is accepted, changed released semantics SHALL
require a greater version. Source and artifact digests SHALL NOT replace that
release boundary.

#### Scenario: Repository manifests are inspected

- **WHEN** Python, root workspace, and launcher package metadata are compared
- **THEN** they resolve to the one product-version authority
- **AND** no manifest retains an independently editable product-version literal

#### Scenario: A stable public contract changes

- **WHEN** a stable release changes its documented public contract
- **THEN** incompatible changes require a major increment, compatible additions or deprecations a minor increment, and compatible fixes a patch increment
- **AND** notes identify compatibility impact and any required migration
- **AND** version syntax, commit subjects and passing tests alone do not prove the chosen increment is correct

#### Scenario: Unpublished source iterations share a release target

- **WHEN** several accepted source commits precede explicit release
- **THEN** they may retain the same next product-release target
- **AND** their exact development build identities remain distinct

#### Scenario: Accepted prerelease semantics advance

- **WHEN** newly accepted product semantics are selected after an explicitly released prerelease
- **THEN** the product version advances according to the compatibility policy
- **AND** the existing release version and artifacts remain unchanged

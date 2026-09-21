## ADDED Requirements

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

#### Scenario: A newer published version is selected

- **WHEN** a channel offers a subsequent accepted release
- **THEN** the target package manager orders it after the prior release
- **AND** a pre-release does not replace a stable installation without explicit selection

## MODIFIED Requirements

### Requirement: Product version has one repository authority

ETHOS SHALL keep one tracked SemVer next product-release target and derive
publishable versions and manifest projections from it. Unpublished source
iterations MAY share that target. Once an explicit release identity is accepted,
changed released semantics SHALL require a greater product version; source and
artifact digests SHALL NOT replace that release boundary.

#### Scenario: Repository manifests are inspected

- **WHEN** Python, root workspace, and launcher package metadata are compared
- **THEN** they resolve to the one product-version authority
- **AND** no manifest retains an independently editable product-version literal

#### Scenario: Unpublished source iterations share a release target

- **WHEN** several accepted source commits precede explicit release
- **THEN** they may retain the same next product-release target
- **AND** their exact development build identities remain distinct

#### Scenario: Accepted prerelease semantics advance

- **WHEN** newly accepted product semantics are selected after an explicitly released prerelease
- **THEN** the product version advances according to the compatibility policy
- **AND** the existing release version and artifacts remain unchanged

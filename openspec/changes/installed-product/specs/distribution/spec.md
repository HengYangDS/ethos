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

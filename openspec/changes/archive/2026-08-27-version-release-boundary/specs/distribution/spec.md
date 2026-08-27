## MODIFIED Requirements

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

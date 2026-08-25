## ADDED Requirements

### Requirement: Product version has one repository authority
ETHOS SHALL keep one tracked SemVer product-version value and SHALL derive every
publishable distribution version and manifest projection from that value.

#### Scenario: Repository manifests are inspected
- **WHEN** Python, root workspace, and launcher package metadata are compared
- **THEN** they resolve to the one product-version authority
- **AND** no manifest retains an independently editable product-version literal.

### Requirement: Product, source, and artifact identities remain distinct
ETHOS SHALL represent the user-comparable product version, exact source
commit/tree, and content-addressed wheel/runtime identities as separate fields.

#### Scenario: Package-only runtime is inspected
- **WHEN** ETHOS runs without access to its source checkout
- **THEN** its immutable manifest reports product and distribution versions,
  source commit/tree, wheel SHA256, runtime digest, channel, and acceptance state
- **AND** no field is inferred from a mutable host path or Forge state.

### Requirement: Unreleased builds are unique and comparable
ETHOS SHALL derive an unreleased PEP 440 distribution identity from the next
product version and exact Git source identity without changing the product
SemVer into a commit identifier.

#### Scenario: Two source commits are built before release
- **WHEN** two distinct source commits share the same next product version
- **THEN** their distribution identities differ and remain PEP 440 parseable
- **AND** neither artifact claims the exact accepted release identity.

### Requirement: Accepted release identity is immutable
ETHOS SHALL reject rollback, reuse, or disagreement of an accepted product
version across source, tag, package metadata, runtime manifest, and artifact
bytes.

#### Scenario: Existing accepted version is rebuilt from different source
- **WHEN** a release request presents a previously accepted version with a
  different source tree or wheel digest
- **THEN** release admission blocks with a stable version-reuse conflict
- **AND** no package, tag, runtime selector, or remote projection changes.

#### Scenario: Local-only release is admitted
- **WHEN** an accepted release has no configured Forge
- **THEN** local repository and artifact evidence can establish the same version
  fact
- **AND** a Forge tag or release is an optional projection, not the version owner.

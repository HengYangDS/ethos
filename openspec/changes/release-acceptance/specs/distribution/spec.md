## MODIFIED Requirements

### Requirement: Accepted release identity is immutable

ETHOS SHALL create an exact release identity only from an explicit release transition and SHALL
reject rollback, source reuse, or artifact disagreement. A release first accepted with its checksum
file SHALL bind the version, the source commit and tree, that file's digest, and the name and
digest of every wheel and archive the file lists. Readers SHALL admit an identity recorded
without that binding, and a version SHALL keep the identity it first recorded. The releasing
host SHALL accept, once, the release that its invoked installation is.

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

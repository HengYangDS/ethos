## MODIFIED Requirements

### Requirement: Accepted release identity is immutable

ETHOS SHALL create an exact release identity only from an explicit release transition and SHALL
reject rollback, source reuse, or artifact disagreement. A release accepted with its checksum file
SHALL bind the version, the source commit and tree, that file's digest, and the name and digest of
every wheel and archive the file lists. Readers SHALL admit an identity recorded without that
binding.

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

- **WHEN** an explicit release transition presents the release's `SHA256SUMS` with the wheel
- **THEN** the accepted identity binds the product version, the source commit and tree, the SHA-256
  of `SHA256SUMS`, and the name and digest of every wheel and archive that file lists
- **AND** the release Attestation names the checksum file's digest among its evidence
- **AND** a transition without the file records the identity as before.

#### Scenario: An identity recorded without the checksum binding is read

- **WHEN** a release Attestation whose payload carries no checksum file digest is read
- **THEN** it yields the same accepted identity as before the binding existed
- **AND** a later acceptance of the same version, source and wheel with its checksum file is
  admitted beside it.

#### Scenario: One version is presented with two checksum files

- **WHEN** a release request presents an accepted version whose bound checksum file digest differs
  from the one already accepted
- **THEN** release admission blocks with the version's artifact conflict
- **AND** no package or Attestation changes.

### Requirement: Public channels consume explicitly accepted release artifacts

ETHOS SHALL project one accepted product-release version to public channels and its matching signed
tag. Published artifacts SHALL be immutable. Development build identities SHALL remain exact local
selections, not automatic channel upgrade versions. Pre-release and stable delivery SHALL remain
distinct. A published file that disagrees with the release's checksum file SHALL refuse the
acceptance that channels consume.

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

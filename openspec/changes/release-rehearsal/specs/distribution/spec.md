## ADDED Requirements

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

## MODIFIED Requirements

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

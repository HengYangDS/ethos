## ADDED Requirements

### Requirement: Minimal Adoption Binding

ETHOS SHALL bootstrap a governed repository with only the strict tracked
binding carrier required by current runtime semantics. Optional documentation,
decision, OpenSpec capability, skill, evidence, release, schema,
generated-artifact, or hosted-provider surfaces SHALL be created only by the
capability that owns them.

#### Scenario: A repository is adopted

- **WHEN** `ethos adopt --apply --authorize --expect-head <HEAD>` runs on an
  eligible Git repository
- **THEN** the planned and written file set SHALL contain only
  `.ethos/profile.toml`
- **AND** the profile SHALL bind a non-empty adopter identity and non-empty
  OpenSpec material paths through the strict frozen repository-profile contract
- **AND** the repository SHALL be recognized as an adopter
- **AND** no `.gitkeep`, provider CI, skill package, generic documentation,
  decision topology, capability family, compatibility state, or optional
  governance carrier SHALL be created.

#### Scenario: Default binding serializes from the typed contract

- **WHEN** ETHOS compiles the default adoption binding
- **THEN** the same strict frozen Pydantic declaration SHALL validate both the
  in-memory binding and its serialized TOML
- **AND** native TOML serialization SHALL produce the tracked binding
- **AND** no adoption-scaffold packaged template, renderer manifest, profile
  registry, family registry, skill registry, digest snapshot, or Jinja render
  environment SHALL be required.

#### Scenario: Parse-only Jinja measurement does not restore adoption rendering

- **WHEN** the product package includes Jinja2 for Budget Contract v2 source
  measurement
- **THEN** adoption SHALL still plan only `.ethos/profile.toml`
- **AND** no Jinja template resource, render environment, or adoption scaffold
  authority SHALL be restored.

#### Scenario: Existing bootstrap content differs

- **WHEN** adoption encounters a differing nonempty, symlinked, non-regular, or
  unreadable `.ethos/profile.toml`
- **THEN** apply SHALL fail with `adoption_conflict:.ethos/profile.toml`
- **AND** no compatibility merge, migration, update, alias, overlay, or parallel
  full scaffold SHALL be offered
- **AND** an empty binding MAY be replaced atomically and identical content MAY
  be retained.

#### Scenario: Unselected optional capabilities do not block a new adopter

- **WHEN** a valid adopter has no matching material change and has not selected
  an optional capability
- **THEN** absent docs, claims, skills, schemas, generated artifacts, hosted
  providers, or OpenSpec workspace carriers SHALL NOT become bootstrap gaps
- **AND** native correctness and material-scope requirements SHALL remain
  independently fail closed.

### Requirement: Current product revision one-binding external-adopter observation is bounded and durable

ETHOS SHALL preserve a provider-neutral observation of the current product
revision against isolated adopter clones using the one binding contract.

#### Scenario: Missing binding is created without unrelated writes

- **WHEN** adoption addresses an isolated clean Git clone without
  `.ethos/profile.toml`
- **THEN** dry-run SHALL plan exactly that one binding carrier
- **AND** authorized exact-HEAD apply SHALL write only that carrier
- **AND** unrelated adopter-owned files and the source seed checkout SHALL remain
  unchanged.

#### Scenario: Existing adopter surfaces reject generic replacement

- **WHEN** adoption encounters a differing nonempty `.ethos/profile.toml`
- **THEN** the observation SHALL record `adoption_conflict:.ethos/profile.toml`
- **AND** unrelated adopter-owned surfaces SHALL remain outside the write plan
- **AND** the source adopter checkout SHALL remain unchanged.

#### Scenario: Current observation is promoted without private coupling

- **WHEN** the raw bundle is promoted into product evidence
- **THEN** the tracked record SHALL omit workstation paths, adopter-private
  identity, credentials, accounts, keys, and provider-local configuration
- **AND** it SHALL bind the product and adopter revisions, one-binding create and
  conflict outcomes, raw-bundle digest, and whether a push occurred
- **AND** it SHALL NOT claim native-backend parity, semantic correctness, hosted
  execution, authority, or independent review unless a separate verifier
  actually establishes that claim.

## MODIFIED Requirements

### Requirement: Adopter First-Hour Contract

ETHOS SHALL provide one first-hour adopter path that is read-only unless apply
is explicitly authorized and exact-HEAD-bound, and that explains the one binding
carrier before mutation.

#### Scenario: Adoption dry-run is inspected

- **WHEN** `ethos adopt --json` runs
- **THEN** the result SHALL report read files, the exact one-file plan, apply
  criteria, conflicts, and rollback instructions
- **AND** profile selection, historical profile names, `init`, explicit
  `--dry-run`, and overlay SHALL not remain as alternate adoption paths.

#### Scenario: Adoption apply is authorized

- **WHEN** adoption is requested with `--apply`
- **THEN** mutation SHALL require `--authorize` and an exact matching
  `--expect-head`
- **AND** a missing repository, authorization, or HEAD match SHALL block before
  the binding is written.

### Requirement: Deterministic Official OpenSpec Tool Supply

ETHOS SHALL invoke the official `@fission-ai/openspec@1.6.0` package from its
repository-owned npx fallback and CI bootstrap while preserving explicit binary,
cached official CLI, and PATH precedence. Adoption SHALL NOT generate an
OpenSpec workspace or provider CI surface.

#### Scenario: ETHOS-owned fallback and CI supply are inspected

- **WHEN** a maintainer inspects the OpenSpec adapter and CI bootstrap
- **THEN** each repository-owned package invocation SHALL identify
  `@fission-ai/openspec@1.6.0`
- **AND** strict official OpenSpec validation SHALL remain the governance gate
- **AND** adoption SHALL plan no OpenSpec or CI carrier.

### Requirement: External-adopter profile evidence has a bounded durable record

ETHOS SHALL record a completed local external-adopter binding exercise through
a dated Chronicle and claim that bind the observed product revision, adopter
revision, binding outcome, and raw-bundle digest without promoting host-local
raw material or provider state into repository truth.

#### Scenario: Local profile evidence is promoted

- **WHEN** an isolated external-adopter binding exercise completes
- **THEN** its claim SHALL bind a dated Chronicle and SHA-256 raw-bundle identity
- **AND** the Chronicle SHALL record exact binding and conflict outcomes
- **AND** it SHALL state whether remote publication was performed.

#### Scenario: Digest-bound evidence is reviewed

- **WHEN** the claim uses digest-only verification
- **THEN** it SHALL NOT claim semantic correctness, hosted-provider execution,
  provider authority, or independent review
- **AND** it SHALL NOT require a named local account, credential, key, daemon,
  or network service.

### Requirement: Authoritative Adopter Material Change Scope Binding

ETHOS SHALL require every valid adopter declaration to carry a non-empty
`[openspec].material_paths` list. For changed paths matching that declaration,
prewrite, changed planning, and proof SHALL use the same selected-Change companion model.
Adoption SHALL emit the complete declaration; no historical profile-write exception remains.
Completed archive companions MAY participate only when their archive is in
current Work Lane scope.

#### Scenario: covered material path is admitted across all surfaces

- **GIVEN** a material path is covered by a valid selected Change companion
- **WHEN** prewrite, changed planning, or proof evaluates that path
- **THEN** the scope binding reports the same coverage fact
- **AND THEN** no material-scope required gap is produced.

#### Scenario: uncovered material path is rejected consistently

- **GIVEN** a declared material path lacks coverage by every valid selected
  companion
- **WHEN** any of prewrite, changed planning, or proof evaluates it
- **THEN** it SHALL report `openspec_material_path_uncovered:<path>`
- **AND THEN** it SHALL not substitute a proof gate, private schema, or method
  package for Change authority.

#### Scenario: incomplete unrelated companions remain diagnostic

- **GIVEN** one official active or archiving Change has a missing or invalid
  companion and another selected Change has a valid matching companion
- **WHEN** a material path covered by the valid companion is evaluated
- **THEN** the path is covered
- **AND** incomplete companion details remain advisory diagnostics rather than
  a global coverage gap.

#### Scenario: declaration and bootstrap fail closed

- **WHEN** an adopter omits, empties, or invalidates `material_paths`
- **THEN** ETHOS SHALL report a material-path declaration gap
- **AND WHEN** an official new Change needs its absent companion created
- **THEN** prewrite MAY admit only that exact untracked Change-local
  `scope.toml` path
- **AND THEN** the completed companion SHALL be syntactically valid, cover
  itself, and cover later material writes.

#### Scenario: existing adopter cannot bootstrap a missing declaration

- **WHEN** a tracked adopter profile lacks `material_paths`
- **THEN** ETHOS SHALL block the write
- **AND** it SHALL NOT emit `profile_material_paths_bootstrap` or admit a second
  profile-write path.

#### Scenario: final archive reconciliation remains covered

- **GIVEN** a completed Change is archived in the current Work Lane change
  scope and its archive has a valid `scope.toml`
- **WHEN** prewrite, changed planning, or proof evaluates a material path from
  that same current scope
- **THEN** the archive companion may cover declared matching paths
- **AND THEN** it SHALL cover paths inside that selected archive directory,
  including the companion itself, only for this reconciliation
- **AND THEN** it SHALL not cover a path outside that archive unless the
  companion explicitly matches it
- **AND** the same scope verdict is returned on all three surfaces.

#### Scenario: historical archive cannot authorize unrelated material work

- **GIVEN** an archive has a valid `scope.toml` but no file from that archive is
  in the current Work Lane change scope
- **WHEN** prewrite, changed planning, or proof evaluates a matching material
  path
- **THEN** the archive is excluded from scope coverage
- **AND** an uncovered path emits `openspec_material_path_uncovered:<path>`.

#### Scenario: archive companion diagnostics remain carrier-invalid

- **GIVEN** a current archive companion is missing or malformed
- **WHEN** lifecycle scope reports its diagnostic
- **THEN** the emitted diagnostic SHALL reduce to the shared carrier-invalid
  invalid-state category
- **AND** it SHALL not grant material-path coverage.

## REMOVED Requirements

### Requirement: Current product HEAD external-adopter observation is bounded and durable

**Reason**: The prior requirement coupled a current-product adoption observation
to native/external command parity even when the isolated one-binding adopter had
no adopter-owned embedded backend. That made a synthetic clone capable of
satisfying the binding contract but incapable of honestly satisfying the parity
scenario.

**Migration**: Use the new current-product-revision one-binding observation for
create/conflict preservation evidence. Run native/external parity only as a
separate exercise against an adopter that actually owns an embedded backend.

### Requirement: Adoption Scaffold

**Reason**: Product source and tests now implement a single typed binding
carrier. The full docs/OpenSpec/skill/provider scaffold and Jinja renderer are no
longer adoption behavior.

**Migration**: Use `ethos adopt` for `.ethos/profile.toml`; create each optional
capability through its owning explicit operation.

### Requirement: Explicit non-destructive adopter overlay

**Reason**: Minimal adoption owns only `.ethos/profile.toml`; unrelated adopter
files are outside the bootstrap write plan, while differing binding content must
fail closed.

**Migration**: Keep adopter-owned files unchanged, invoke `ethos adopt` for the
single missing binding manifest, and use each optional capability's explicit
operation for later projections.

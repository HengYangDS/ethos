## MODIFIED Requirements

### Requirement: Minimal Adoption Binding

ETHOS SHALL bootstrap a governed repository with only the strict tracked
binding carrier required by current runtime semantics. It SHALL NOT preallocate
optional documentation, decision, OpenSpec capability, skill, evidence,
release, schema, generated-artifact, or hosted-provider surfaces.

#### Scenario: A repository is adopted

- **WHEN** `ethos adopt --apply` runs on an empty Git repository
- **THEN** the planned and written file set SHALL contain only
  `.ethos/profile.toml`
- **AND** the profile SHALL bind a non-empty adopter identity and non-empty
  OpenSpec material paths through the strict frozen repository-profile contract
- **AND** the repository SHALL be recognized as an adopter
- **AND** no `.gitkeep`, provider CI, skill package, generic documentation,
  decision topology, capability family, or compatibility state SHALL be created.

#### Scenario: Default binding serializes from the typed contract

- **WHEN** ETHOS compiles the default adoption bootstrap
- **THEN** the same strict frozen Pydantic declaration SHALL validate both the
  in-memory binding and its serialized TOML
- **AND** no packaged template, Jinja environment, manifest, renderer taxonomy,
  profile registry, family registry, skill registry, digest snapshot, or
  generated Python source SHALL be required.

#### Scenario: Unselected optional capabilities do not block a new adopter

- **WHEN** a valid adopter has no material change and has not explicitly
  selected docs, claims, skills, schemas, generated-artifacts, hosted-provider,
  or OpenSpec workspace capabilities
- **THEN** their absent carriers SHALL NOT add required gaps to adoption,
  planning, or the default adopter proof floor
- **AND** missing native code-correctness declarations SHALL remain visible as
  `adopter_profile_missing_code_correctness_gates` rather than being replaced by
  optional-capability gaps.

#### Scenario: A declared material change activates OpenSpec fail-closed scope

- **WHEN** a changed path matches the adopter profile's declared
  `[openspec].material_paths`
- **THEN** planning, proof, and prewrite SHALL require a valid selected Change
  companion that covers the path
- **AND** absent coverage SHALL report
  `openspec_material_path_uncovered:<path>`.

#### Scenario: Existing bootstrap content differs

- **WHEN** adoption encounters a differing nonempty `.ethos/profile.toml`
- **THEN** apply SHALL fail with `adoption_conflict:.ethos/profile.toml`
- **AND** no compatibility merge, migration, update, alias, overlay, or parallel
  full scaffold SHALL be offered.

### Requirement: Adopter First-Hour Contract

ETHOS SHALL provide one first-hour adopter path that is read-only unless apply
is explicitly authorized and that explains the exact binding carrier before
mutation.

#### Scenario: Adoption dry-run is inspected

- **WHEN** `ethos adopt --json` runs
- **THEN** the result SHALL report read files, the exact one-file plan, apply
  criteria, conflicts, and rollback instructions
- **AND** profile selection, historical profile names, `init`, explicit
  `--dry-run`, and overlay SHALL not remain as alternate adoption paths.

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
- **AND** the Chronicle SHALL record the exact binding and conflict outcomes
- **AND** it SHALL state whether remote publication was performed.

#### Scenario: Digest-bound evidence is reviewed

- **WHEN** the claim uses digest-only verification
- **THEN** it SHALL NOT claim semantic correctness, hosted-provider execution,
  provider authority, or independent review
- **AND** it SHALL NOT require a named local account, credential, key, daemon,
  or network service.

### Requirement: Current product HEAD external-adopter observation is bounded and durable

ETHOS SHALL preserve a provider-neutral current-product observation against an
isolated adopter clone using the one binding contract and shared command plane.

#### Scenario: Existing adopter surfaces reject generic replacement

- **WHEN** adoption encounters a differing nonempty `.ethos/profile.toml`
- **THEN** the observation SHALL record `adoption_conflict:.ethos/profile.toml`
- **AND** unrelated adopter-owned surfaces SHALL remain outside the write plan
- **AND** the source adopter checkout SHALL remain unchanged.

#### Scenario: Native and external command surfaces are compared

- **WHEN** the product runtime addresses the isolated adopter clone
- **THEN** the record SHALL bind both revisions and bounded parity outcomes
- **AND** it SHALL NOT claim semantic correctness, hosted execution, remote
  publication, authority, or independent review.

#### Scenario: Current observation is promoted without private coupling

- **WHEN** the raw bundle is promoted into product evidence
- **THEN** the tracked record SHALL omit workstation paths, adopter-private
  identity, credentials, accounts, keys, and provider-local configuration
- **AND** it SHALL bind the raw-bundle digest and state whether a push occurred.

### Requirement: Authoritative Adopter Material Change Scope Binding

ETHOS SHALL require every valid adopter declaration to carry a non-empty
`[openspec].material_paths` list. Prewrite, changed planning, and proof SHALL use
the same selected-Change companion model. Adoption SHALL emit the complete
declaration, so no historical profile-write exception remains. Completed archive
companions MAY participate only when their archive is in current Work Lane scope.

#### Scenario: covered material path is admitted across all surfaces

- **WHEN** a material path is covered by a valid selected Change companion
- **THEN** prewrite, changed planning, and proof SHALL return the same coverage
  fact without a material-scope gap.

#### Scenario: uncovered material path is rejected consistently

- **WHEN** no selected valid companion covers a declared material path
- **THEN** every surface SHALL report `openspec_material_path_uncovered:<path>`
- **AND** no proof gate, private schema, or method package SHALL substitute for
  Change authority.

#### Scenario: incomplete unrelated companions remain diagnostic

- **WHEN** one selected companion is invalid and another valid companion covers
  the path
- **THEN** the path SHALL remain covered
- **AND** the invalid companion SHALL remain a diagnostic rather than a global
  coverage gap.

#### Scenario: declaration and bootstrap fail closed

- **WHEN** an adopter omits, empties, or invalidates `material_paths`
- **THEN** ETHOS SHALL report the declaration gap
- **AND WHEN** a new official Change needs its absent `scope.toml`
- **THEN** prewrite MAY admit only that exact Change-local companion, which SHALL
  cover itself and later material writes.

#### Scenario: existing adopter bootstraps a missing profile declaration

- **WHEN** a tracked adopter profile lacks `material_paths`
- **THEN** ETHOS SHALL block the write
- **AND** it SHALL NOT emit `profile_material_paths_bootstrap` or admit a second
  profile-write path.

#### Scenario: final archive reconciliation remains covered

- **WHEN** a completed Change archive is part of current Work Lane scope and its
  companion covers a current material path
- **THEN** all three surfaces MAY use that companion for this reconciliation
- **AND** it SHALL NOT cover undeclared paths outside the archive.

#### Scenario: historical archive cannot authorize unrelated material work

- **WHEN** an archive is absent from current Work Lane scope
- **THEN** it SHALL be excluded from coverage even when its patterns match.

#### Scenario: archive companion diagnostics remain carrier-invalid

- **WHEN** a current archive companion is missing or malformed
- **THEN** its diagnostic SHALL reduce to carrier-invalid
- **AND** it SHALL grant no material-path coverage.

## REMOVED Requirements

### Requirement: Explicit non-destructive adopter overlay

**Reason**: Minimal adoption owns only `.ethos/profile.toml`; preserving or
classifying unrelated adopter files is outside the bootstrap boundary, while a
differing binding manifest must fail closed.

**Migration**: Keep adopter-owned files unchanged, invoke `ethos adopt` for the
single missing binding manifest, and use each optional capability's explicit
operation for any later projection.

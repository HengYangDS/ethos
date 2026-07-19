## MODIFIED Requirements

### Requirement: Authoritative Adopter Material Change Scope Binding

ETHOS SHALL require each adopter profile to declare a non-empty
`[openspec].material_paths` pattern list. For every changed material path,
`ethos lane prewrite`, `ethos plan --changed`, and `ethos prove` SHALL use the
same ETHOS-owned `scope.toml` companion read model over the official OpenSpec
active or archiving Change selection. `scope.toml` remains a companion beside a
Change, not an OpenSpec workflow-schema extension. A legacy adopter MAY
bootstrap only its already-tracked `.ethos/profile.toml` declaration against
exactly one official active Change; that fallback applies only to this one
profile-only write and SHALL NOT make that Change cover any other material
path. A completed archive MAY participate only when the archive itself
contributes to the current Work Lane change scope; it remains excluded for all
unrelated future changes. A selected tracked malformed Change-local
`scope.toml` MAY be admitted only to repair that exact companion; it SHALL NOT
provide coverage until its repaired declaration is valid.

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

#### Scenario: tracked invalid companion repairs only itself

- **GIVEN** exactly one selected active Change has a Git-tracked malformed
  `scope.toml`
- **AND** prewrite evaluates exactly that companion path
- **WHEN** the shared scope reader evaluates the request
- **THEN** it MAY report `tracked_scope_repair_admitted` with the exact Change
  and companion path
- **AND** it SHALL NOT mark the malformed companion as coverage
- **AND** an unselected or widened material-path request SHALL remain uncovered.

#### Scenario: existing adopter bootstraps a missing profile declaration

- **GIVEN** a valid tracked adopter profile has no `material_paths` declaration
- **AND** exactly one official active Change is selected
- **WHEN** prewrite evaluates only `.ethos/profile.toml`
- **THEN** ETHOS MAY admit that write with
  `profile_material_paths_bootstrap` provenance
- **AND THEN** an explicit empty or malformed declaration, or a request that
  includes another path, SHALL remain blocked
- **AND THEN** later material writes SHALL require ordinary Change-local scope
  coverage.

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

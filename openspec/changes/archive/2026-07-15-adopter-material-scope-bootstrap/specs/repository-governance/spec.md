## MODIFIED Requirements

### Requirement: Authoritative Adopter Material Change Scope Binding

ETHOS SHALL require each adopter profile to declare a non-empty
`[openspec].material_paths` pattern list. For every changed material path,
`ethos lane prewrite`, `ethos plan --changed`, and `ethos prove` SHALL use the
same ETHOS-owned `scope.toml` companion read model over the official OpenSpec
active or archiving Change selection. `scope.toml` remains a companion beside a
Change, not an OpenSpec workflow-schema extension.

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

#### Scenario: declaration and bootstrap fail closed

- **WHEN** an adopter omits, empties, or invalidates `material_paths`
- **THEN** ETHOS SHALL report a material-path declaration gap
- **AND WHEN** an official new Change needs its absent companion created
- **THEN** prewrite MAY admit only that exact `scope.toml` path
- **AND THEN** the completed companion SHALL cover itself and later material
  writes.

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

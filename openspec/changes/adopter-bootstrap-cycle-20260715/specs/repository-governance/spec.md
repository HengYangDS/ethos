## MODIFIED Requirements

### Requirement: Adopter Material Change Scope Binding

ETHOS SHALL require an adopter that uses OpenSpec lifecycle governance to
declare a non-empty `[openspec].material_paths` profile list. For every changed
material path, `ethos lane prewrite`, `ethos plan --changed`, and `ethos prove`
SHALL use the same ETHOS-owned `scope.toml` companion read model over the
official OpenSpec active or archiving Change selection. The companion is not an
official OpenSpec workflow-schema extension. A legacy adopter MAY bootstrap
only its already-tracked `.ethos/profile.toml` declaration against exactly one
official unarchived Change with status `no-tasks`; that fallback SHALL apply
only to this one profile-only write and SHALL NOT make that Change cover any
other material path.

#### Scenario: material path is covered by a selected Change

- **GIVEN** an adopter profile declares a material path and an officially
  selected Change has a valid matching `scope.toml` companion
- **WHEN** prewrite, changed planning, or proof evaluates that path
- **THEN** all three surfaces SHALL report the same coverage fact
- **AND** no material-scope required gap is emitted.

#### Scenario: material path is uncovered

- **GIVEN** a declared material path lacks coverage from every valid selected
  Change companion
- **WHEN** prewrite, changed planning, or proof evaluates the path
- **THEN** the surface SHALL report
  `openspec_material_path_uncovered:<path>`
- **AND** it SHALL not substitute a native proof gate, private schema, or
  method package for Change authority.

#### Scenario: declaration and bootstrap fail closed

- **WHEN** an adopter omits, empties, or invalidates `material_paths`
- **THEN** lifecycle SHALL report a material-path declaration gap
- **AND WHEN** the official active list identifies a new Change with no
  companion
- **THEN** prewrite MAY admit only that Change's exact absent `scope.toml`
- **AND** the completed companion SHALL cover itself and later material writes.

#### Scenario: fresh official Change bootstraps only the legacy profile

- **GIVEN** exactly one official unarchived Change has status `no-tasks`
- **AND** the existing adopter profile is tracked and lacks the declaration
- **WHEN** prewrite evaluates only `.ethos/profile.toml`
- **THEN** it SHALL admit the profile bootstrap for that Change
- **AND** it SHALL NOT admit any additional path or use the Change to cover a
  normal material write.

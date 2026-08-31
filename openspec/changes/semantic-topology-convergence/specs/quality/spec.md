## MODIFIED Requirements

### Requirement: Semantic And Physical Isomorphism

Repository-owned code SHALL place each narrow concept with one truth or effect
owner and one primary reason to change. A package directory and its modules
SHALL express a real semantic boundary rather than implementation convenience.
Ambiguous modules, facades, aliases, private cross-module imports, mixed command
owners, empty package shells, and mechanical suffix splits SHALL block proof.

#### Scenario: A generic module has no closed semantic contract

- **WHEN** the module-layout gate observes `core`, `common`, `shared`, `utils`,
  `helpers`, `base`, `manager`, `service`, or another configured ambiguous name
- **THEN** the module must be absorbed, precisely renamed, split on a real
  semantic axis, or deleted
- **AND** splitting only to satisfy ELOC or retaining the old path as a facade
  is not remediation

#### Scenario: An empty package shell is observed

- **WHEN** a package contains only `__init__.py` and has no child package,
  resource boundary, registration boundary, or public import boundary
- **THEN** the package SHALL be deleted and its consumers SHALL import the
  concrete owner or its parent package
- **AND** an empty `__init__.py` SHALL NOT be retained as a marker

#### Scenario: A package contains one implementation module

- **WHEN** a package contains exactly one implementation module and no child
  package or independent package-level boundary
- **THEN** the module SHALL move to the nearest semantic parent and the package
  SHALL be deleted
- **AND** the move SHALL be rejected as a mechanical simplification if the
  package owns a distinct public namespace, resource boundary, registration
  boundary, or independent reason to change

#### Scenario: A package has only an initializer and child packages

- **WHEN** a package contains no implementation module but contains child
  packages
- **THEN** it SHALL be retained only when its path is a deliberate semantic
  namespace or public boundary documented by its consumers
- **AND** otherwise its children SHALL be moved to the nearest real semantic
  parent and the shell SHALL be deleted

#### Scenario: A suffix split is proposed

- **WHEN** one module is split into same-level files differing only by a
  historical suffix such as `_core`, `_helpers`, `_impl`, or `_runtime`
- **THEN** the split SHALL be rejected unless each resulting owner has a
  distinct invariant, consumer boundary, and primary reason to change
- **AND** a real multi-owner boundary SHALL use a semantic subpackage rather
  than a flat suffix family

#### Scenario: Physical layout is audited after a move

- **WHEN** module-layout proof evaluates the repository
- **THEN** every moved symbol has one defining owner, every consumer resolves to
  that owner, and no retired path, facade, or private import remains
- **AND** the audit SHALL report the exact path and owner relation for every
  missing, duplicate, orphan, or conflicting result

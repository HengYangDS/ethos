## ADDED Requirements

### Requirement: No dead carriers

A declared repository path SHALL name content at the current head: a tracked file, a directory that holds a tracked file other than a README, or a glob that matches one. A README that is its directory's only file, a contract key that no reader consumes, and a format root that admits no tracked file of its format SHALL each be a gap. A shipped catalog that names adopter paths SHALL NOT be held to this repository's content.

#### Scenario: A rule glob names a removed directory

- **WHEN** `.ethos/rules.toml` declares `tools/ci/scripts/**` and no tracked file matches it
- **THEN** reference closure reports `semantic_declaration_missing:path:tools/ci/scripts/**:.ethos/rules.toml`

#### Scenario: A README outlives its directory's content

- **WHEN** `system/projections/README.md` is the only file of its directory
- **THEN** docs health reports `docs_readme_without_children:system/projections/README.md`

#### Scenario: A contract declares a table that no reader consumes

- **WHEN** `system/surfaces.toml` declares a table or surface field that its schema does not define
- **THEN** the system contracts report a schema violation for `surfaces`

#### Scenario: A format root admits no tracked file

- **WHEN** the format selection policy allows a root that holds no tracked file of its format
- **THEN** format selection fails and names that root

#### Scenario: A reference names a directory that retired files emptied

- **WHEN** a carrier references a directory, and every file under it was retired
- **THEN** reference closure reports that carrier as a consumer of the retired files
- **AND** a reference to a directory that still holds content is not a consumer

#### Scenario: A shipped catalog names an adopter path

- **WHEN** the packaged gate registry, the paradigm or the artifact topology names a path that this repository does not hold
- **THEN** no dead-carrier gap is reported for it

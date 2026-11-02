## ADDED Requirements

### Requirement: Declared names and carrier paths have one source

The paradigm SHALL be the one source of the branch role names, the binding root and files, the
version source and the changelog. Product code SHALL build each from the declaration, and an
architecture check SHALL report any other string constant in `src/` or `tools/`, docstrings aside,
that contains a binding carrier path or file name or equals the version source, the changelog or a
multi-segment branch role value.

#### Scenario: Product code restates a binding carrier

- **WHEN** a product module passes `.ethos/release.toml` as a string constant
- **THEN** the architecture check reports the file and line.

#### Scenario: A gap code names a binding carrier

- **WHEN** a gap code names `.ethos/profile.toml`
- **THEN** its value is built from the declaration and is unchanged.

#### Scenario: A branch role is read without arguments

- **WHEN** a branch role policy is built without arguments
- **THEN** it carries the names that the paradigm's `[branch]` table declares.

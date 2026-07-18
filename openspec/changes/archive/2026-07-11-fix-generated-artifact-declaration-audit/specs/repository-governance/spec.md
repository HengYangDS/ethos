## ADDED Requirements

### Requirement: Entrypoint audits distinguish declarations from producers

The generated-artifact entrypoint audit SHALL evaluate executable producer commands and SHALL NOT treat declarative cleanup, ignore, exclude, or forbidden-path configuration as evidence that the entrypoint produces generated state in a denied home.

#### Scenario: Structured manifest declares cleanup and ignore paths

- **WHEN** `pyproject.toml` contains denied-home tokens only in cleanup paths, ignore globs, exclusion lists, or local-state declarations
- **THEN** the entrypoint audit reports no producer gap for those declarations
- **AND** the denied path topology remains enforced if matching generated files actually exist

#### Scenario: Structured manifest task writes to a denied home

- **WHEN** a supported task command in `pyproject.toml` actively writes a cache or package artifact to a denied home
- **THEN** the entrypoint audit emits the corresponding denied-home producer gap
- **AND** declaration-only filtering does not suppress the finding

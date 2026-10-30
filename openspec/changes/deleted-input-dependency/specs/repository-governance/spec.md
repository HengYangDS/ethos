## MODIFIED Requirements

### Requirement: Deletion admission preserves affected consumers

Exact patch admission SHALL retain deleted paths and evaluate affected surviving
native consumers against the effective postimage. It SHALL permit removal with
consumer updates, reject a surviving required input and preserve unknown coverage
when the required native relationship cannot be resolved. A deleted Python module
whose top-level package a dependency of the repository's Python project provides
under the same normalized name SHALL NOT count as a surviving required input.

#### Scenario: Authored configuration and consumer retire together

- **WHEN** a patch removes configuration and updates its explicit native consumer
- **THEN** no generation exception is needed and the closed deletion is admitted
- **AND** preimages, caller ownership and exact paths remain checked

#### Scenario: Required native consumer survives

- **WHEN** a patch removes a file still selected as an explicit native input
- **THEN** admission blocks and names the deleted input and surviving consumer
- **AND** unchanged consumers are not omitted because they have no patch entry

#### Scenario: A declared dependency replaces a deleted package

- **WHEN** a patch deletes a vendored Python package that surviving code imports
- **AND** the effective root `pyproject.toml` declares a dependency of the same normalized name
  that is not the project's own name
- **THEN** admission does not report the imports as deleted inputs
- **AND** deleting the project's own package, or a package that only a dependency of another name
  declares, still blocks

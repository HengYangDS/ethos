## ADDED Requirements

### Requirement: Source-built hook runtime installs the locked closure

ETHOS SHALL install a source-built immutable hook runtime from the project's
locked dependency closure without network access or transitive re-resolution.

#### Scenario: Locked offline runtime installation

- **GIVEN** a source checkout with `pyproject.toml` and `uv.lock`
- **WHEN** ETHOS builds and installs its package-only hook runtime
- **THEN** the runtime installation SHALL consume the locked closure offline
- **AND** SHALL NOT select a transitive version absent from the lock.

#### Scenario: Lock unavailable

- **GIVEN** source runtime materialization cannot consume its declared lock
- **WHEN** installation is attempted
- **THEN** ETHOS SHALL fail closed
- **AND** SHALL NOT fall back to unlocked or network resolution.

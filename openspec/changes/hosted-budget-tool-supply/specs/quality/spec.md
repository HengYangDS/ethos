## ADDED Requirements

### Requirement: Hosted budget tool supply

Hosted verification SHALL prepare the declared source-budget cross-check
executable from versioned, digest-bound native supply before executing gates.
Both Forge projections SHALL consume the same preparation owner without system
installation or reliance on undeclared host executables.

#### Scenario: Clean supported runner

- **WHEN** a supported runner has no ambient cross-check executable
- **THEN** preparation verifies the declared archive and executable version
- **AND** hosted gates receive the project-local executable on their effective PATH

#### Scenario: Invalid or unavailable supply

- **WHEN** the archive, checksum, executable version or supported target is unavailable or invalid
- **THEN** verification fails before tests with the original supply diagnostic
- **AND** stale passing receipts and test reports cannot represent this attempt

#### Scenario: Verified cached archive

- **WHEN** the declared archive exists in the project cache
- **THEN** preparation verifies it again before restoring the executable
- **AND** changed cached executable bytes are not trusted as the declared supply

#### Scenario: Unchanged verified executable

- **WHEN** the cached executable is a regular executable with bytes matching the verified archive
- **THEN** preparation rechecks its version without rewriting or replacing the file
- **AND** reuse still rejects a corrupt archive or failed version observation

#### Scenario: Damaged cached executable

- **WHEN** the cached executable is missing, altered, non-executable or a symbolic link
- **THEN** preparation validates a replacement before atomically installing it
- **AND** it does not write through the symbolic link or change its target

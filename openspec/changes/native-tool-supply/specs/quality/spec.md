## RENAMED Requirements

- FROM: `### Requirement: Hosted budget tool supply`
- TO: `### Requirement: Native verification tool supply`

## MODIFIED Requirements

### Requirement: Native verification tool supply

Native verification tools SHALL use one materialization owner reading their
versioned, digest-bound declarations. Supply SHALL use controlled cache storage,
never system installation or ambient executable trust. Preparation SHALL verify
regular archive members, executable bytes and version; serialize concurrent
writers and atomically replace only the selected executable. Invalid supply
SHALL preserve prior bytes and remove owned preparation scratch.

#### Scenario: Clean supported runner

- **WHEN** a supported runner lacks an ambient scanner or budget executable
- **THEN** preparation verifies and installs both declared tools in owned cache storage
- **AND** callers receive their exact directories without administrator privileges

#### Scenario: Invalid or unavailable supply

- **WHEN** the archive, digest, executable version or platform is invalid or unavailable
- **THEN** verification fails before tests with the original supply diagnostic
- **AND** prior executable bytes remain unchanged and owned scratch is removed
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

#### Scenario: Repeated or concurrent preparation

- **WHEN** multiple invocations request the same declared tool identity
- **THEN** a bounded lock serializes preparation and verified unchanged bytes are reused
- **AND** invocation count does not create additional archives or executable generations

#### Scenario: Cache path escapes through a link

- **WHEN** a selected cache path is symlinked or otherwise unsafe
- **THEN** preparation rejects it before writing or replacing external content

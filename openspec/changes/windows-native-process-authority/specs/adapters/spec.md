## ADDED Requirements

### Requirement: Shared external process execution has one adapter owner

ETHOS SHALL execute shared external argv commands through one provider-neutral
process adapter. The Git adapter SHALL own only Git executable resolution and
Git-specific semantics; it SHALL NOT own the generic command runner used by
OpenSpec, hooks, runtime activation, or host-native authorities. Process
creation failures SHALL preserve the exact argv, working directory, and
operating-system cause at the public diagnostic boundary.

#### Scenario: A non-Git command cannot be created

- **WHEN** an ETHOS adapter invokes an exact non-Git command and the operating
  system rejects process creation
- **THEN** the failure is classified as process execution rather than Git
  execution
- **AND** its evidence contains the exact argv, working directory, and original
  operating-system cause.

#### Scenario: Git process creation fails

- **WHEN** the Git adapter resolves Git but the operating system rejects that
  exact process creation
- **THEN** the public failure retains Git-specific classification
- **AND** the same exact argv, working directory, and original operating-system
  cause remain available.

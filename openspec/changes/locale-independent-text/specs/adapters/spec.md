## MODIFIED Requirements

### Requirement: Shared external process execution has one adapter owner

ETHOS SHALL execute shared external argv commands through one provider-neutral process adapter. The
Git adapter SHALL own only Git executable resolution and Git-specific semantics; it SHALL NOT own
the generic command runner used by OpenSpec, hooks, runtime activation, or host-native authorities.
Process creation failures SHALL preserve the exact argv, working directory, and operating-system
cause at the public diagnostic boundary. The adapter SHALL decode a command's text output and encode
its text input as UTF-8 unless the caller declares the encoding that the command always writes; the
host locale SHALL NOT select a process text encoding.

#### Scenario: A non-Git command cannot be created

- **WHEN** an ETHOS adapter invokes an exact non-Git command and the operating system rejects
  process creation
- **THEN** the failure is classified as process execution rather than Git execution
- **AND** its evidence contains the exact argv, working directory, and original operating-system
  cause.

#### Scenario: Git process creation fails

- **WHEN** the Git adapter resolves Git but the operating system rejects that exact process creation
- **THEN** the public failure retains Git-specific classification
- **AND** the same exact argv, working directory, and original operating-system cause remain
  available.

#### Scenario: A host locale differs from UTF-8

- **WHEN** a command writes UTF-8 text on a host whose locale encoding is GBK or code page 1252
- **THEN** the adapter returns the same text as on a UTF-8 host
- **AND** text the adapter writes to the command's standard input is UTF-8.

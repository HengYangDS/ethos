## ADDED Requirements

### Requirement: Native command failures keep their complete outcome

When a native command fails or times out at a boundary that turns it into evidence, ETHOS SHALL keep
its argv, its exit status or bound, and its complete standard output and standard error;
human-facing messages MAY stay bounded. A provider gate whose deadline expires SHALL report
`gate_timeout:<gate>` as unknown with the bound and the elapsed seconds, as a command gate does.

#### Scenario: Both streams are present

- **WHEN** a provider's native command exits nonzero after writing 2,140 bytes to each stream
- **THEN** the gate's `gate_provider_error` diagnostic carries the argv, the exit status and both
  streams complete

#### Scenario: A stream is empty

- **WHEN** a failed command writes only to standard error
- **THEN** its outcome records an empty standard output and the complete standard error

#### Scenario: A provider times out

- **WHEN** a provider gate declares `timeout_seconds = 1` and its provider runs longer
- **THEN** the gate reports `gate_timeout:<gate>` with verdict unknown, the bound and the elapsed
  seconds

#### Scenario: Git refuses the text classification

- **WHEN** `git ls-files --eol` exits 128 while ETHOS classifies authored text
- **THEN** the failure keeps Git's exit status and stderr instead of reading unobserved
- **AND** a successful classification that omits a path still reads unobserved

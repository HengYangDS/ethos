## ADDED Requirements

### Requirement: Content-addressed package publication is host portable

ETHOS SHALL publish immutable package bytes with file durability, atomic
identity establishment, and collision verification on every supported host.
It SHALL apply an additional parent-directory durability barrier only where the
host supports opening and synchronizing directory descriptors.

#### Scenario: Windows publishes an immutable package

- **WHEN** ETHOS materializes a content-addressed package on Windows
- **THEN** it flushes the complete file and atomically establishes the digest path
- **AND** it does not attempt the unsupported POSIX directory-descriptor operation.

#### Scenario: POSIX preserves the directory durability barrier

- **WHEN** ETHOS materializes a content-addressed package on a supported POSIX host
- **THEN** it synchronizes the containing directory after atomic publication
- **AND** any directory open or synchronization failure remains fatal.

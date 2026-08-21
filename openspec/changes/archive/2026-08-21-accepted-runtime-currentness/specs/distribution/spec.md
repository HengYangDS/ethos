## ADDED Requirements

### Requirement: Package-only hook runtime carries accepted source identity
Every non-editable ETHOS wheel used to materialize a Git-hook runtime SHALL carry
one immutable build identity containing the exact ETHOS source commit and source
tree. The runtime manifest SHALL bind that identity together with its wheel,
Python ABI, platform, executable, and entrypoint bytes.

#### Scenario: wheel is built from an ETHOS checkout
- **WHEN** a non-editable wheel is built from a Git-backed ETHOS source tree
- **THEN** the wheel contains its exact source commit and source tree as package data
- **AND** an installed runtime copies those values into its single manifest identity

#### Scenario: runtime is installed without a source checkout
- **WHEN** hook installation runs from an installed wheel outside an ETHOS source checkout
- **THEN** it derives source identity from the wheel's packaged build identity
- **AND** it does not require a live checkout, host-local database, or absolute build path

#### Scenario: legacy manifest lacks source identity
- **WHEN** runtime observation encounters the retired integrity-only manifest schema
- **THEN** the runtime is non-current and cannot authorize hook execution
- **AND** the reader returns the public repair action rather than invoking a compatibility reader

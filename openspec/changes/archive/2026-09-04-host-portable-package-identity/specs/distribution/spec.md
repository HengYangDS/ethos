## MODIFIED Requirements

### Requirement: Package-only hook runtime carries accepted source identity

Every non-editable ETHOS wheel used to materialize a Git-hook runtime SHALL carry
one immutable build identity containing the exact ETHOS source commit and source
tree. A clean checkout of that commit SHALL compile the same source tree on every
supported host under repository-owned Git content semantics. An installed wheel
outside a selected runtime SHALL resolve its originating local wheel from its
PEP 610 `file:` URL using native path semantics before validating the packaged
identity. The runtime manifest SHALL bind that identity together with its wheel,
Python ABI, operating system, CPU architecture, executable, and entrypoint bytes.

#### Scenario: wheel is built from an ETHOS checkout

- **WHEN** a non-editable wheel is built from a Git-backed ETHOS source tree
- **THEN** the wheel contains its exact source commit and source tree as package data
- **AND** an installed runtime copies those values into its single manifest identity

#### Scenario: clean source checkout crosses host text defaults

- **GIVEN** two supported hosts check out the same exact ETHOS commit under
  different ambient text-conversion defaults
- **WHEN** each host compiles the source build identity without a real overlay
- **THEN** both identities contain the commit's exact `HEAD^{tree}` value
- **AND** checkout presentation does not create a host-specific distribution version

#### Scenario: installed wheel uses a native file URL

- **WHEN** a provenance-bound installed distribution reports its originating
  wheel through a valid local PEP 610 `file:` URL
- **THEN** ETHOS converts that URL through the current host's native path semantics
- **AND** validates and reuses that exact wheel without a source checkout or
  platform-specific path rewrite

#### Scenario: runtime is installed without a source checkout

- **WHEN** hook installation runs from an installed wheel outside an ETHOS source checkout
- **THEN** it derives source identity from the wheel's packaged build identity
- **AND** it does not require a live checkout, host-local database, or absolute build path

#### Scenario: legacy manifest lacks source identity

- **WHEN** runtime observation encounters the retired integrity-only manifest schema
- **THEN** the runtime is non-current and cannot authorize hook execution
- **AND** the reader returns the public repair action rather than invoking a compatibility reader

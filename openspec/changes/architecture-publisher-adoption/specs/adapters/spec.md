## ADDED Requirements

### Requirement: Source-owned Architecture Publisher integration

ETHOS SHALL own the sole mutable adapter and live Edition that translate its
exact terminal-architecture projection into Architecture Publisher public
contracts. The integration SHALL remain an optional downstream package and
SHALL NOT become an ETHOS command, governance kernel, or second source of
repository truth.

#### Scenario: ETHOS architecture is compiled

- **WHEN** the integration receives an explicitly selected ETHOS projection and
  an exact compatible Architecture Publisher package
- **THEN** it emits source, Claim Model, Edition, Candidate, and media values
  through Architecture Publisher public contracts
- **AND** it does not compile Commitments, issue repository permission, manage
  Work Lanes, execute CAS effects, mint ETHOS proof, or reinterpret acceptance.

#### Scenario: The integration is installed away from both repositories

- **WHEN** exact package archives and portable inputs are installed in a relocated
  directory with empty user configuration and no adjacent checkout discovery
- **THEN** the same selected Candidate is reproduced offline
- **AND** every source, renderer, package, and artifact identity is explicit.

#### Scenario: Migration staging reaches source-owned parity

- **WHEN** the ETHOS-owned package and the Publisher migration package consume
  the same immutable inputs
- **THEN** their Candidate and sibling-media identities are identical
- **OR** the difference is recorded as an explicit semantic successor requiring
  fresh review
- **AND** only then may the Publisher repository remove its mutable ETHOS copy.

#### Scenario: Publisher capability is absent

- **WHEN** the optional integration package or a compatible Publisher package is
  not installed
- **THEN** ordinary ETHOS governance, proof, installation, and release continue
  unchanged
- **AND** ETHOS does not fetch, infer, or silently activate the integration.

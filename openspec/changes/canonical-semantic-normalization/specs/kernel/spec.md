## MODIFIED Requirements

### Requirement: Semantic identity is schema-versioned and runtime-independent

A supported semantic carrier SHALL be interpreted by exactly one immutable
schema-version protocol. Identity-bearing defaults, normalization, canonical
projection, and digest domain SHALL NOT vary between source, wheel, package-only
runtime, host, or process. Semantic collection input order SHALL NOT determine
validity or identity; the contract owner SHALL validate members and normalize
them before identity projection.

#### Scenario: The same v2 carrier is interpreted in several runtimes

- **WHEN** exact bytes are loaded from the same Git tree
- **THEN** every runtime produces the same semantic identity
- **AND** a changed interpreter requires a new schema version

#### Scenario: A current v1 carrier is encountered after cutover

- **WHEN** normal plan compilation or mutation loads it
- **THEN** ETHOS blocks before deriving current semantic authority
- **AND** only the exact one-shot bootstrap may consume its persisted Lease tuple

#### Scenario: Equivalent collection permutations are loaded

- **WHEN** two supported carriers contain the same valid semantic collection
  members in different physical orders
- **THEN** both produce the same typed value, canonical JSON, and digest
- **AND** repeated canonical projection is idempotent

#### Scenario: A semantic collection contains duplicate or conflicting members

- **WHEN** normalization observes a duplicate identity or a field-specific
  semantic conflict
- **THEN** ETHOS rejects the carrier before deriving authority
- **AND** sorting never hides or resolves the conflict

#### Scenario: Exact canonical bytes are required by a storage boundary

- **WHEN** a reader consumes an already content-addressed canonical JSON envelope
- **THEN** it MAY reject byte-level non-canonical representation
- **AND** that check SHALL NOT make ordinary typed input order semantically invalid

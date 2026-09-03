## MODIFIED Requirements

### Requirement: Semantic identity is schema-versioned and runtime-independent

A supported semantic carrier SHALL be interpreted by exactly one immutable
schema-version protocol. Identity-bearing defaults, normalization, canonical
projection, and digest domain SHALL NOT vary between source, wheel, package-only
runtime, host, or process. Semantic collection input order SHALL NOT determine
validity or identity; the contract owner SHALL validate members and normalize
them before identity projection. Every JSON value used to derive semantic
identity, an authority-bearing signature payload, or an admission digest SHALL
use the same kernel-owned closed canonical byte projection. Exact raw-content,
Git-object, native-program, and presentation bytes SHALL remain under their
native owners and SHALL NOT redefine semantic JSON identity.

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

#### Scenario: Semantic JSON identity crosses entry paths

- **WHEN** equivalent valid JSON meaning reaches Commitment, Attestation, Facts,
  TransitionPlan, policy, rule, or independent-verification identity through
  different public entry paths
- **THEN** every path consumes the same canonical UTF-8 bytes
- **AND** Unicode object keys use the one declared ordering
- **AND** values outside the closed semantic grammar fail before hashing or
  signing

#### Scenario: A composed admission projection binds exact observations

- **WHEN** an admission projection contains exact raw-file, Git-entry, or
  implementation digests as members
- **THEN** those nested digests continue to identify their native bytes
- **AND** the enclosing typed admission projection uses the one semantic JSON
  byte protocol

#### Scenario: Exact canonical bytes are required by a storage boundary

- **WHEN** a reader consumes an already content-addressed canonical JSON envelope
- **THEN** it MAY reject byte-level non-canonical representation
- **AND** that check SHALL NOT make ordinary typed input order semantically invalid

#### Scenario: Non-semantic bytes are bound

- **WHEN** ETHOS hashes a raw file, wheel, runtime inventory member, Git object,
  Git transaction program, or rendered output
- **THEN** the native owner hashes the exact relevant bytes
- **AND** the semantic JSON canonicalizer does not normalize or reinterpret them

#### Scenario: A projected checksum has no identity consumer

- **WHEN** a report or normalized projection emits a checksum that no current
  comparison, lookup, signature, CAS, or validation consumes
- **THEN** the checksum and any schema or prose requiring it are removed
- **AND** the underlying typed projection remains available to its real readers

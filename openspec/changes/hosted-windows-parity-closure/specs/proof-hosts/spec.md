## ADDED Requirements

### Requirement: Host conformance controls repository-local Git semantics

ETHOS SHALL make portable host-conformance assertions independent of ambient
Git text-conversion defaults by declaring the exact repository-local semantics
required by each fixture.

#### Scenario: CRLF bytes are tested on a Windows-style Git configuration

- **WHEN** the adopter fixture stages a CRLF byte sequence while
  `core.autocrlf=true`
- **THEN** its tracked fixture policy preserves the exact bytes in the index
- **AND** the working tree and staged blob round-trip identically.

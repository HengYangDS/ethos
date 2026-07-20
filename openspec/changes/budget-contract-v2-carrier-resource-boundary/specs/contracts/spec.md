## ADDED Requirements

### Requirement: Versioned Carrier Resource Boundary

ETHOS SHALL admit Budget Contract v2 native measurement only when every
resolved provider has a versioned execution contract that bounds carrier bytes
before allocation or parser construction. The boundary SHALL be part of the
metric/provider identity and SHALL NOT vary by repository path.

#### Scenario: Metric contracts bind one provider resource contract

- **WHEN** a metric registry is loaded or one carrier profile is resolved
- **THEN** every metric atom SHALL declare an admitted execution mode and a
  strict positive maximum carrier byte count
- **AND** all atoms for the same provider SHALL declare the same mode and ceiling
  across roles, profiles, and metrics
- **AND** those fields SHALL enter metric-registry, resolved-contract, native,
  carrier, and snapshot identities
- **AND** a missing, forged, mixed, defaulted, path-specific, or unknown resource
  declaration SHALL fail closed.

#### Scenario: Oversize worktree carrier is rejected before reading

- **WHEN** a classified regular worktree carrier has a pre-read size above its
  resolved provider ceiling
- **THEN** ETHOS SHALL reject it before the first content read
- **AND** a permitted read SHALL retain no more than `limit + 1` bytes while
  checking growth and the existing descriptor/path fingerprint
- **AND** a pre-read or post-read oversize result SHALL expose one stable
  repository-relative gap without exception text or partial bytes
- **AND** the carrier and complete measurement snapshot SHALL be absent.

#### Scenario: Direct native callers cannot bypass the reader boundary

- **WHEN** direct native bytes exceed the exact resolved provider ceiling
- **THEN** native admission SHALL reject them before startup conformance,
  dependency probing, UTF-8 decoding, AST construction, or provider parsing
- **AND** it SHALL return no metric values, normalized stream, or partial digest.

#### Scenario: C1 preserves authority and later-stage boundaries

- **WHEN** the versioned byte boundary is accepted
- **THEN** v1 source-budget and per-file ELOC SHALL remain unchanged and
  authoritative
- **AND** v2 SHALL remain inactive
- **AND** immutable Git replay, provider-gap repair, vector policy, Debt v2,
  changed-scope admission, dual control, cutover, and global v1 LOC retirement
  SHALL require their later governed Changes.

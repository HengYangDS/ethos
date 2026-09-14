## ADDED Requirements

### Requirement: Attestation materialization avoids member-linear process creation

The existing Git set owner SHALL construct canonical set trees using bounded
native batch invocations rather than one process per member. It SHALL preserve
exact bytes, modes, object-format identity, caller index and deterministic CAS
union semantics. Temporary inputs SHALL have one bounded owner and be removed
on normal and exception exits.

#### Scenario: Set grows while repository contents remain unchanged

- **WHEN** a writer records canonical members into an existing selected set
- **THEN** Git process count for blob and index construction does not grow with member count
- **AND** the resulting set is byte-identical to native canonical construction
- **AND** the caller's index and worktree remain unchanged

#### Scenario: Batch fails or CAS loses

- **WHEN** native materialization fails or another writer wins the ref CAS
- **THEN** failure does not move the selected ref or overwrite the caller index
- **AND** owned staging is removed and a losing CAS reobserves the current union

### Requirement: Pure Attestation reuse does not reuse current authority

Attestation readers MAY reuse successful canonical validation of identical raw
bytes in bounded process-local memory. Each read SHALL freshly observe selected
membership, object bytes and framing. Ref, predicate, policy, identity, validity
and effect admission SHALL remain fresh. Missing objects, malformed reads and
invalid changed bytes SHALL fail identically with warm or empty reuse state.

#### Scenario: Identical members are read repeatedly

- **WHEN** a reader observes identical bounded-size canonical bytes again
- **THEN** pure canonical validation is reused without changing the returned values
- **AND** cold reads, eviction and oversized uncached members produce the same meaning

#### Scenario: Current selection or observation changes after a warm read

- **WHEN** the selected ref changes, a member disappears or native object reading fails
- **THEN** the new selection or failure is observed instead of a prior cached verdict
- **AND** no historical value authorizes an effect

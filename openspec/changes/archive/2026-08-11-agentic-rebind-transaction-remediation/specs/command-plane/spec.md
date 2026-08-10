# Command plane delta

## ADDED Requirements

### Requirement: Commitment rebind coordinates are publicly derived

ETHOS SHALL provide a read-only derive operation that converts the current
owned Work Lane observations and one exact compatible signed target commit into
a digest-bound Commitment-rebind request receipt.

#### Scenario: Exact target is derived

- **GIVEN** one valid Lease is held by the invocation actor and exactly one
  signed dangling target commit represents the staged Commitment transition
- **WHEN** rebind derivation runs
- **THEN** ETHOS returns the old and new carrier paths, bytes digests, semantic
  digests, HEAD, tree, index, overlay, Lease generation, target OID, receipt
  path, and receipt digest
- **AND** the caller supplies business intent rather than copying those internal
  coordinates.

#### Scenario: Target derivation is ambiguous

- **WHEN** zero or more than one compatible signed target is observable
- **THEN** derivation blocks without selecting one
- **AND** it reports the observed candidate OIDs and the unique public next
  command when a mechanical next step exists.

### Requirement: Commitment rebind apply consumes an exact receipt

ETHOS SHALL allow rebind dry-run and apply to consume a derive receipt and SHALL
revalidate all mutable coordinates before effect execution.

#### Scenario: Unchanged receipt applies

- **WHEN** receipt-bound apply observes the same holder, Lease generation, HEAD,
  tree, index, overlay, target commit, signature trust, and carrier semantics
- **THEN** the existing exact Git and Lease transaction applies
- **AND** the terminal receipt binds the derive receipt digest and all effects.

#### Scenario: Any coordinate drift fails closed

- **WHEN** any receipt-bound coordinate changes before dry-run or apply
- **THEN** ETHOS reports a typed `missing`, `mismatch`, `stale`, `drift`, or
  `authority_denied` blocker naming observed and expected values
- **AND** no Git ref or Lease effect is applied.

### Requirement: Commitment rebind failures are directly actionable

ETHOS SHALL recognize an active Commitment transition as a dedicated lifecycle
condition and project one typed remediation rather than a generic ref or bytes
mismatch.

#### Scenario: Normal commit creates a valid dangling target

- **WHEN** hook admission prevents the Work Lane ref from advancing because the
  active Commitment changed but the signed target object was created
- **THEN** ETHOS reports `commitment_rebind_required`
- **AND** it returns the valid target OID, old and new carrier digests, partial
  effects, and the one copy-safe derive command
- **AND** it tells the caller not to repeat the commit.

#### Scenario: Structured remediation remains bounded

- **WHEN** a lifecycle blocker is emitted
- **THEN** its remediation identifies the owner, reason, observed and expected
  values, whether mutation or user decision is required, retryability, and one
  existing public next command
- **AND** full diagnostics remain available through an immutable artifact
  reference rather than an unbounded default payload.

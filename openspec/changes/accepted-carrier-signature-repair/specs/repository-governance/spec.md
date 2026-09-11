## ADDED Requirements

### Requirement: Signature-only payload preservation

ETHOS SHALL compare signature replacements by exact complete commit bytes after
removing only Git signature headers and their continuation lines. Tree, ordered
parents, author, committer, dates, encoding, unknown headers and message bytes
SHALL remain unchanged. Same-tree or normalized-text equality SHALL NOT establish
signature-only equivalence.

#### Scenario: Non-signature header bytes differ

- **WHEN** a replacement adds or removes a carriage return in an encoding header
- **THEN** signature-only equivalence is false
- **AND** no payload normalization conceals the difference

#### Scenario: Only signature headers differ

- **WHEN** distinct commits have identical complete non-signature payloads
- **THEN** the payload comparator reports signature-only equivalence
- **AND** separate current trust verification is still required before repair

#### Scenario: Root and merge commit payloads are preserved

- **WHEN** repair creates a replacement for a root or merge commit
- **THEN** its zero or multiple ordered parents and complete payload remain exact
- **AND** unsupported native signing inputs fail without moving refs

### Requirement: Bounded accepted signature replacement

ETHOS SHALL admit replacement only from the current accepted policy, explicit
authorization, an exact unsigned source, a trusted signed replacement, selected
ref coordinates and clean linked worktrees. Each effect SHALL recheck its own
preconditions. Existing effect evidence SHALL support recovery without becoming
reusable authorization.

#### Scenario: Select only required local refs

- **WHEN** current policy identifies the accepted ref and coupled local projections
- **THEN** the plan binds every selected ref to its observed old and desired OID
- **AND** independent release, topic and remote refs remain unchanged
- **AND** an unrelated candidate OID is neither overwritten nor silently included

#### Scenario: Trust and payload are independent conditions

- **WHEN** a replacement has a trusted signature but different preserved bytes
- **THEN** repair rejects it
- **AND** an equal payload with an untrusted signature is also rejected

#### Scenario: Drift blocks the next effect

- **WHEN** a bound ref, policy, trust input, index or linked worktree has changed
- **THEN** the next affected mutation is rejected with the precise coordinate
- **AND** already observed effects remain accurately reported

#### Scenario: Partial worktree synchronization recovers safely

- **WHEN** selected refs moved but one linked worktree could not synchronize
- **THEN** the result identifies completed and remaining effects
- **AND** recovery re-observes refs and worktrees before continuing
- **AND** unrelated content and refs remain unchanged

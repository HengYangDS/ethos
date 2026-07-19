## ADDED Requirements

### Requirement: Versioned local-state schema evolution

ETHOS SHALL evolve ignored SQLite local state through ordered, transactional
schema migrations that preserve active coordination and record the applied
schema version only after successful completion.

#### Scenario: A version-1 state database is opened

- **WHEN** ETHOS initializes a version-1 database that still contains the retired
  empty `cache_entries` table
- **THEN** it removes that table and records schema version 2 in one successful
  migration
- **AND** existing leases, events, chronicle events, and retrieval data remain
  available.

#### Scenario: A current database is initialized again

- **WHEN** ETHOS initializes a database that already records schema version 2
- **THEN** the migration is idempotent
- **AND** no active coordination row is rewritten or deleted.

### Requirement: Explicit conservative local-state maintenance

ETHOS SHALL keep local-state audit read-only by default and SHALL require an
explicit maintenance action before pruning disposable state.

#### Scenario: Audit runs without maintenance authorization

- **WHEN** the local-state owner runs in its default audit mode
- **THEN** it reports migration residue, lease candidates, proof candidates, and
  ignored-state inventory
- **AND** it does not mutate SQLite, proofs, refs, worktrees, or snapshots.

#### Scenario: Expired orphan leases are maintained

- **WHEN** explicit maintenance evaluates an expired lease whose branch ref,
  linked worktree, and recorded path are all absent
- **THEN** ETHOS deletes that exact lease row and reports its identity
- **AND** it retains every unexpired, current, ambiguous, or still-observable
  lease.

### Requirement: Ref-bound proof retention

ETHOS SHALL treat HEAD-keyed local proof as disposable readiness state while
preserving the current HEAD record and every proof whose commit remains reachable
from a current Git ref.

#### Scenario: A proof HEAD is unreachable from all refs

- **WHEN** explicit maintenance finds a well-formed proof record whose named Git
  HEAD is not reachable from any current ref and is not current HEAD
- **THEN** it removes that proof record and reports its path and HEAD
- **AND** current or ref-reachable proof records remain unchanged.

### Requirement: Recovery material is preservation-bound before cleanup

ETHOS SHALL NOT delete a recovery snapshot set until a complete operator archive
and a digest-bound Chronicle receipt have been verified.

#### Scenario: Recovery snapshots contain unique Git and dirty-worktree material

- **WHEN** an operator closes a recovery snapshot set
- **THEN** the archive manifest binds every entry, archive digest, byte size,
  bundle verification result, archive location, and repository HEAD
- **AND** extraction and bundle verification succeed before the source snapshot
  directory is removed.

### Requirement: Accepted-root closeout is bound to one audited candidate HEAD

ETHOS SHALL bind candidate audit, control-replacement admission, executed proof,
and accepted-root mutation to one observed candidate HEAD.

#### Scenario: Candidate HEAD changes during or after closeout audit

- **WHEN** accepted-root closeout observes the candidate HEAD before audit
- **THEN** the audit receives that HEAD as its claim binding
- **AND** closeout re-observes the candidate after audit and immediately before
  mutation
- **AND** any mismatch blocks control admission and accepted-root movement.

## REMOVED Requirements

### Requirement: Reference adapter stays provider-local and constrained

**Reason:** The bundled independent-identity reference executable was historical
scaffolding rather than product authority. Retaining a product-shipped executable
would blur the operator/provider trust boundary fixed by DR-0006.

**Migration:** Operators may supply a conforming one-shot verifier outside the
ETHOS product source and distribution surface. Product code retains the signed
provider-neutral receipt contract, protected provider configuration, exact Git
and proof-floor bindings, and fail-closed admission.

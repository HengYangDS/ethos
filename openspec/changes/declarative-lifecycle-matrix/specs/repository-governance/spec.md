## ADDED Requirements

### Requirement: Lease generation transitions compile from one declaration

ETHOS SHALL define renew, resume, handoff-offer, and handoff-accept operation
IDs, guard requirements, planned and applied states, and effect fields in the
tracked workflow declaration. The CLI SHALL supply current facts to one pure
reducer and SHALL dispatch only the effect named by the resulting
declaration-owned plan.

#### Scenario: A declared lease generation transition is evaluated

- **WHEN** renew, resume, handoff offer, or handoff accept is requested
- **THEN** ETHOS loads the matching declared lease transition
- **AND** the pure reducer returns its ordered gaps and state
- **AND** no parallel procedural operation matrix owns the same behavior.

### Requirement: Linked Work Lane retirement has one generation-bound effect

ETHOS SHALL route ordinary landed and superseded linked Work Lane retirement
through one semantic owner and one strict request contract. Before any
destructive effect, it SHALL bind the current actor to the exact lease row and
payload identity, holder, epoch, lane ref, expected head, row expiry, and raw
payload digest under a SQLite generation lock. It SHALL recheck the accepted
control root, accepted
head, lane relation, linked checkout head, and dirty state. It SHALL remove only
a clean linked checkout and SHALL compare-and-delete only the exact lane ref
through a Git ref transaction that also verifies the accepted ref.

#### Scenario: Exact lease generation changed after planning

- **WHEN** the lease ID, holder, epoch, lane ref, expected head, row expiry, or
  raw payload digest no longer matches the planned linked retirement
- **THEN** ETHOS blocks the effect
- **AND** it leaves the linked worktree, lane ref, and current lease intact.

#### Scenario: Accepted ref changes during linked retirement

- **WHEN** the accepted ref differs after the worktree is removed but before the
  lane ref transaction commits
- **THEN** the Git ref transaction rejects lane-ref deletion
- **AND** the SQLite lease deletion rolls back
- **AND** ETHOS reports a blocked partial transition without claiming retirement.

#### Scenario: Lease commit fails after Git removal

- **WHEN** the clean worktree and exact lane ref were removed but the SQLite
  transaction cannot commit
- **THEN** ETHOS rolls back the lease deletion
- **AND** it restores the exact lane ref only if that ref remains absent
- **AND** it reports whether the no-clobber compensation succeeded.

#### Scenario: Landed and superseded commands share one owner

- **WHEN** a caller invokes ordinary landed or superseded linked retirement
- **THEN** both CLI commands construct the same strict request model and call
  the same linked-retirement effect
- **AND** no wrapper, re-export, compatibility summary, or parallel Python effect
  remains.

### Requirement: Lease generation identity is complete across boundaries

ETHOS SHALL represent one exact lease generation with its lease ID, holder,
epoch, lane ref, expected head, row expiry, and raw payload SHA-256 across
workspace status, handoff packages, accepted Chronicle bindings, retirement
attempts, receipts, and mutation effects. It SHALL reject incomplete or stale
bindings and SHALL NOT support a parallel legacy fingerprint.

#### Scenario: Handoff or Chronicle omits a mutable lease fact

- **WHEN** an otherwise matching lease binding omits or changes row expiry or
  raw payload SHA-256
- **THEN** ETHOS rejects the handoff or exceptional retirement
- **AND** the current lease and carrier remain unchanged.

#### Scenario: Unavailable-holder recovery is admitted

- **WHEN** accepted policy admits unavailable-holder retirement for one complete
  foreign lease generation
- **THEN** ETHOS calls the same exact revoke primitive used by ordinary holder
  relinquishment
- **AND** no unavailable-holder wrapper or parallel destructive effect exists.

#### Scenario: Cross-host destination import is acknowledged

- **WHEN** the package target actor imports one verified handoff package
- **THEN** ETHOS creates one destination-local Lease generation
- **AND** its content-addressed acknowledgement binds the package, target holder,
  lane/head, incarnation, Lease ID, epoch, expected head, expiry, and payload
  SHA-256
- **AND** edited, incomplete, or non-target acknowledgements cannot authorize
  source revocation.

#### Scenario: Cross-host import fails after Lease acquisition

- **WHEN** destination restoration fails after the new Lease is acquired
- **THEN** ETHOS removes only the exact created Git carriers
- **AND** revokes only that exact Lease generation after carrier absence is
  proven
- **AND** uncertain compensation retains observable state and fails closed.

#### Scenario: The same content-addressed package is exported again

- **WHEN** the derived package directory already exists
- **THEN** ETHOS verifies and reuses the identical immutable package
- **AND** it never recursively deletes or replaces existing package content.

### Requirement: Work Lane start is no-clobber and compensation-bound

ETHOS SHALL reject a Work Lane start before lease acquisition when the target
path or lane ref already exists. It SHALL recheck both after acquiring the new
lease. If Git worktree creation fails, ETHOS SHALL remove only a linked
worktree and ref proven to match the requested path, branch, and leased expected
head. It SHALL revoke the newly acquired lease only after both exact carriers
are proven absent.

#### Scenario: Target carrier already exists

- **WHEN** the requested target path or lane ref exists before lease acquisition
- **THEN** ETHOS blocks Work Lane start
- **AND** it creates no lease and does not modify the existing carrier.

#### Scenario: Carrier cleanup is incomplete

- **WHEN** failed Work Lane creation cannot remove the exact linked worktree or
  compare-and-delete the exact lane ref
- **THEN** ETHOS retains the lease
- **AND** it reports the failed cleanup boundary without claiming rollback.

#### Scenario: Failed creation leaves no carrier

- **WHEN** Git worktree creation fails and every carrier created by the attempt
  is proven absent
- **THEN** ETHOS revokes only the newly acquired exact lease generation
- **AND** unrelated leases, paths, and refs remain unchanged.

### Requirement: Archived evidence does not own runtime replay

ETHOS SHALL NOT hard-code one archived Claim ID, dated archive carrier, or fixed
historical file set into Work Lane rebase execution. It SHALL resolve generated
parity conflicts through the parity projection path and declarative source-budget
ledger conflicts through the generic semantic ledger path.

#### Scenario: Historical one-off conflict shape reappears

- **WHEN** a rebase conflict matches a retired Claim-specific file set
- **THEN** ETHOS does not auto-resolve it from the historical Claim or archive
- **AND** the generic current conflict rules either resolve it or fail closed.

## MODIFIED Requirements

### Requirement: Versioned local-state schema evolution

ETHOS SHALL support exactly the current subject-keyed Work Lane lease schema,
with canonical generation state in `payload_json` and SQLite-enforced
one-lease-per-subject uniqueness. The lease subsystem SHALL own only the
`leases` table and its non-partial binary unique subject constraint within the
shared local-state database. ETHOS SHALL NOT migrate retired lease shapes,
retain a lease-owned database-wide version ledger, or reject unrelated tables
owned by other local-state capabilities. Unsupported lease state fails closed
and must be recreated through the canonical lifecycle.

#### Scenario: A fresh state database is initialized

- **WHEN** no state schema exists
- **THEN** ETHOS creates the current subject-keyed lease schema
- **AND** SQLite enforces subject uniqueness
- **AND** it does not create a database-wide migration ledger.

#### Scenario: A version-1 state database is opened

- **WHEN** ETHOS opens a database whose `leases` table has a retired shape or a
  noncanonical subject constraint
- **THEN** ETHOS fails closed without translating or rewriting the database
- **AND** current local coordination must be recreated through the canonical
  lifecycle.

#### Scenario: Another owner shares the state database

- **WHEN** the current lease table coexists with tables owned by another
  local-state capability
- **THEN** lease initialization validates only its exact owned schema subset
- **AND** it preserves every unrelated table and row unchanged.

#### Scenario: A current database is initialized again

- **WHEN** the exact current subject-keyed lease schema already exists
- **THEN** initialization is idempotent
- **AND** no active coordination row is rewritten or deleted.

## ADDED Requirements

### Requirement: Retained Topic Retirement

ETHOS SHALL allow an explicitly selected clean local topic to retire without
claiming accepted absorption when every target commit remains reachable from
another explicitly selected, surviving local topic ref. This deletion-only
transition SHALL reuse the existing retirement owner, exact Git effect,
Lease coordination, immutable receipt, and recovery mechanism.

#### Scenario: Redundant clean history is retained by a local descendant
- **WHEN** an authorized actor requests `lane retire superseded` from the
  accepted control root with an exact target HEAD and a distinct local
  `refs/heads/...` retention ref containing that HEAD
- **THEN** the plan binds target deletion, accepted HEAD, retained ref and OID,
  target worktree cleanliness, and current target Lease coordinates
- **AND** successful apply removes only the target worktree, ref, and applicable
  Lease, leaving accepted and retained objects and retained checkout unchanged
- **AND** the result reports history retention rather than accepted semantics

#### Scenario: Retention or deletion coordinates do not hold
- **WHEN** the target is dirty, protected, candidate, stale, or foreign-owned,
  or the retained ref is missing, identical, protected, candidate, or unrelated
- **THEN** retirement fails closed without deleting any target resource

#### Scenario: Retained ref moves after derivation
- **WHEN** the exact retained ref no longer resolves to its planned OID
- **THEN** preflight rejects before worktree removal
- **AND** the Git transaction independently checks the retained-ref assertion
  atomically with deletion, preserving existing partial-effect recovery

#### Scenario: Historical topic lacks current authoring policy
- **WHEN** the accepted owner has admitted one exact retirement intent for a
  historical topic whose own policy cannot be compiled
- **THEN** the reference-transaction hook consumes accepted policy and that exact
  intent without granting authoring rights or accepting a raw unplanned deletion

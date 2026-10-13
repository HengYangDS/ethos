## MODIFIED Requirements

### Requirement: Merge continuation binds exact native state

ETHOS SHALL offer merge continuation through its existing refresh boundary.
Starting SHALL select the fresh candidate ref. Once native Git records a pending
merge, continuation SHALL bind its selected immutable parent and exact Lane ref,
index, content, runtime and holder generation. Continuing SHALL preserve both
parents and declared commit policy without coupling to later candidate movement.
Subsequent candidate integration SHALL independently observe and CAS its target.

#### Scenario: Pending merge is unresolved

- **WHEN** a Work Lane contains a native merge with unmerged index stages
- **THEN** status identifies that operation and its conflict paths
- **AND** it does not prescribe a new rebase or claim readiness to integrate.

#### Scenario: Resolved merge advances the lane

- **WHEN** the current owner accepts an exact resolved index and unchanged parents
- **THEN** the common commit and CAS owners create and admit the two-parent result
- **AND** proof and candidate integration remain separate subsequent obligations.

#### Scenario: Coordinates or authority change

- **WHEN** runtime, holder generation, Lane ref, pending parent, index or working
  content no longer matches the preview
- **THEN** apply rejects before changing the lane ref or merge projection.

#### Scenario: Candidate advances while the pending merge is resolved

- **WHEN** the candidate ref advances before continuation preview or apply
- **THEN** continuation preserves the recorded pending parent and resolved tree
- **AND** it updates only the Lane ref under its exact original-head CAS
- **AND** the newer candidate ref and its worktree remain unchanged.

#### Scenario: Continuation acknowledgement is lost

- **WHEN** the exact Lane effect completed but acknowledgement or projection
  cleanup was interrupted
- **THEN** native recovery recognizes that original effect without repeating CAS
- **AND** unrelated candidate progress does not invalidate that recovery.

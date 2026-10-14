## MODIFIED Requirements

### Requirement: Merge continuation binds exact native state

ETHOS SHALL offer merge continuation through its existing refresh boundary.
Starting SHALL select the fresh candidate ref by default. Explicit merge source
selection SHALL accept only an existing full Work Lane ref, bind its source head
in the preview and effect assertion, and reject rebase or changed source selection.
For a pending merge the selected source SHALL contain its recorded parent without
replacing that immutable parent. Once native Git records a pending
merge, continuation SHALL bind its selected immutable parent and exact Lane ref,
index, content, runtime and holder generation. Continuing SHALL preserve both
parents and declared commit policy without coupling to later candidate movement.
Subsequent candidate integration SHALL independently observe and CAS its target.
Continuation authoring scope SHALL derive from the staged tree's native diff
against the original parents' Git three-way composition. Existing contributions
SHALL remain distinct from newly authored resolution. Reconstructing that
baseline SHALL NOT modify the source index, worktree or refs. Complete staged
admission and official Change validation SHALL remain required; native import or
composition SHALL NOT grant ownership of incoming Change progress.
Native source extraction SHALL validate active Change identities once through
the canonical identifier owner. Invalid incoming identities SHALL make the
observation unavailable regardless of the authored path set.

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

#### Scenario: Explicit intent coexists with an unchanged incoming Change

- **WHEN** continuation selects the local Change and the index retains the
  incoming Change's exact bytes and modes
- **THEN** authoring scope excludes those unchanged imports without rewriting them
- **AND** complete staged admission and official validation remain required
- **AND** a changed incoming task state remains refused.

#### Scenario: Both parents already contributed to another Change

- **WHEN** the index preserves the original parents' native composition of that
  Change's bytes and modes
- **THEN** continuation preserves both contributions without assigning their
  earlier authoring to the selected local Change
- **AND** a new resolution outside the selected Change remains refused.

#### Scenario: Candidate advances while the pending merge is resolved

- **WHEN** the candidate ref advances before continuation preview or apply
- **THEN** continuation preserves the recorded pending parent and resolved tree
- **AND** it updates only the Lane ref under its exact original-head CAS
- **AND** the newer candidate ref and its worktree remain unchanged.

#### Scenario: Existing peer contribution is selected explicitly

- **WHEN** merge strategy selects a full Work Lane ref containing the pending parent
- **THEN** preview and effect bind that source ref's exact current head
- **AND** continuation preserves the original parents and resolved index
- **AND** candidate and protected refs remain unchanged.

#### Scenario: Explicit source is invalid or changes after preview

- **WHEN** the source is missing, malformed, protected, unrelated to the pending
  parent, requested with rebase, or moves after preview
- **THEN** the existing public boundary refuses before the lane effect
- **AND** it preserves HEAD, native merge metadata and staged content.

#### Scenario: Incoming Change identity is invalid

- **WHEN** the incoming tree contains an invalid active Change identity
- **THEN** continuation reports that incoming Change observation is unavailable
- **AND** empty or unrelated authored paths do not conceal or change that refusal.

#### Scenario: Continuation acknowledgement is lost

- **WHEN** the exact Lane effect completed but acknowledgement or projection
  cleanup was interrupted
- **THEN** native recovery recognizes that original effect without repeating CAS
- **AND** unrelated candidate progress does not invalidate that recovery.

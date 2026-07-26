## ADDED Requirements

### Requirement: Clean ownerless divergence distinguishes retained lineage from unique intent

ETHOS SHALL require an accepted, target-bound semantic judgment before retiring
any clean linked Work Lane that has no current lease or Claim and is diverged
from accepted truth. The judgment MUST distinguish history retained by an exact
valid-owner descendant from unique intent that requires a verified preservation
package, and it SHALL grant no authority over the valid-owner lane.

#### Scenario: exact predecessor history remains reachable from valid-owner descendants

- **GIVEN** a clean missing-lease predecessor has an exact branch and HEAD
- **AND** fresh Git observation proves that HEAD is an ancestor of every named
  valid-owner semantic receiver
- **WHEN** accepted Chronicle evidence selects `lane_resolution/retire`
- **THEN** native resolution SHALL recheck the predecessor and descendant
  containment without mutating any valid-owner lane
- **AND** any accepted-ancestor effect boundary SHALL block without source
  deletion and require a separate accepted reconciliation before a changed
  disposition.

#### Scenario: unique clean divergence is preserved before retirement

- **GIVEN** a clean missing-lease lane contains committed intent reachable from
  no other branch or tag
- **AND** accepted truth does not adopt that intent
- **WHEN** accepted Chronicle evidence selects
  `lane_resolution/preserve-retire`
- **THEN** ETHOS SHALL create and verify the exact recovery package before
  removing only the named source branch and worktree
- **AND** preservation SHALL NOT claim semantic acceptance, remote publication,
  or authority to clear the package.

#### Scenario: valid-owner or dirty state remains protected

- **WHEN** fresh observation finds a valid lease, Claim-bound owner, dirty
  overlay, changed HEAD, changed registration, or lost descendant containment
- **THEN** housekeeping and exceptional resolution SHALL leave that lane intact
- **AND** the outcome SHALL remain a bounded blocker rather than a cleanup
  success claim.

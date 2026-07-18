## ADDED Requirements

### Requirement: Committed Adopter Profile Policy At Closeout

ETHOS SHALL resolve adopter proof policy from the promoted committed tree when
accepted-root closeout evaluates an exact candidate advance before the accepted
worktree has reset to that candidate commit.  The implementation of this policy
SHALL remain subject to the active proof floor; a proof failure SHALL be
remediated in a separately active Change without weakening closeout policy,
source-budget limits, evidence binding, or the raw-reference-move guard.

#### Scenario: candidate proof policy is evaluated during accepted-root closeout

- **GIVEN** a candidate commit changes a valid non-product repository profile
  that defines its native proof gates
- **WHEN** a reference-transaction hook evaluates the proposed accepted-root
  advance before the accepted worktree resets to that candidate commit
- **THEN** ETHOS SHALL resolve the profile, required proof floor, gate
  descriptors, policy digest, and run conformance from the promoted committed
  tree
- **AND** a profile absent from that resolvable candidate tree SHALL be treated
  as absent rather than inherited from the accepted-old working tree
- **AND** raw accepted-root moves without a matching one-shot closeout intent
  SHALL remain blocked.

#### Scenario: closeout-policy remediation does not lower the acceptance bar

- **GIVEN** a Change introduces committed-profile closeout policy resolution
- **WHEN** it is prepared for candidate landing
- **THEN** it SHALL preserve candidate-tree policy resolution and the
  raw-reference-move guard
- **AND** it SHALL pass the existing proof floor without adding source-budget
  debt, allowance, or an exclusion for the remediation
- **AND** regenerated evidence and later proof SHALL bind the corrective HEAD.

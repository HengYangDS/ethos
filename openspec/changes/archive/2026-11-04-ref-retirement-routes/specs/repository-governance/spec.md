## ADDED Requirements

### Requirement: Absorbed-ref retirement previews agree with the prepared hook

An absorbed-ref retirement preview SHALL evaluate the reference-transaction hook's legacy role protection and ref-move policy resolution through the hook's own predicates, without claiming the retirement's intent. A deletion that the hook would refuse for either reason SHALL block the preview with the hook's gap, and the preview SHALL NOT emit an apply command for it.

#### Scenario: A protected legacy role ref

- **WHEN** an absorbed-ref retirement selects a ref that the accepted head's committed table declares as a legacy role name, and no successor ref holds its commit
- **THEN** the preview blocks with `legacy_role_ref_protected` and names the accepted closeout
- **AND** it emits no apply command.

#### Scenario: No strict policy governs the deletion

- **WHEN** neither the deleted commit nor the accepted head carries a release binding or a valid profile
- **THEN** the preview blocks with `ref_move_policy_unavailable`
- **AND** it emits no apply command.

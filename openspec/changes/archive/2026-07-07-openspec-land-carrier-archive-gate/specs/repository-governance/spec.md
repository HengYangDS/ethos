## MODIFIED Requirements

### Requirement: OpenSpec carriers are archived before promotion

ETHOS SHALL allow active OpenSpec carriers as Work Lane authoring context but
SHALL block land, candidate closeout, and accepted-root closeout when active
carriers remain unarchived.

#### Scenario: Work Lane active carrier blocks land

- **GIVEN** a Work Lane contains `openspec/changes/<id>` outside `archive`
- **AND** the Work Lane is otherwise clean and proof-bound
- **WHEN** `ethos land --apply` evaluates mutation admission
- **THEN** land is blocked with `openspec_active_change_unarchived:<id>:work_lane`
- **AND** the carrier must be archived/fused before promotion

#### Scenario: Completed active carrier keeps specific repair signal

- **GIVEN** a Work Lane contains an active OpenSpec change whose tasks are all complete
- **WHEN** mutation admission evaluates OpenSpec carrier gaps
- **THEN** the gap is `openspec_completed_change_unarchived:<id>`
- **AND** ETHOS does not also emit a less specific active-carrier gap for the same id

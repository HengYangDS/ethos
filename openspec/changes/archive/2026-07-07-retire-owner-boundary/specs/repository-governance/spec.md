# repository-governance Delta

## MODIFIED Requirements

### Requirement: Foreign Work Lane retirement requires owner authority

A landed Work Lane MUST NOT be retired merely because it is visible, merged, and
clean. Retirement authority MUST be bound to the Work Lane lease owner or an
explicit higher-authority handoff or break-glass path.

#### Scenario: Foreign landed lane remains observe-only

- **WHEN** a landed Work Lane has no active lease owner matching the current actor
- **THEN** `ethos lane retire-landed` reports `foreign_work_lane_retire_authority_required`
- **AND** the Work Lane worktree and branch remain intact

#### Scenario: Owner-bound landed lane may retire

- **WHEN** a landed Work Lane is merged, clean, HEAD-bound, and the current actor matches its lease owner
- **THEN** `ethos lane retire-landed --apply` may remove the worktree and delete the branch

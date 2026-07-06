# command-plane Delta

## MODIFIED Requirements

### Requirement: Self OpenSpec Lifecycle Mode

ETHOS CLI SHALL expose OpenSpec lifecycle review through the public ETHOS
command plane.

#### Scenario: OpenSpec lifecycle surfaces protected branch residue

- **WHEN** `ethos openspec --lifecycle --json` runs from a clean current checkout
- **THEN** active OpenSpec carriers in non-current protected branch Git trees are exposed as advisory gaps
- **AND** the payload includes `lifecycle.protected_branch_residue` records naming branch, role, change, and gap
- **AND** the advisory residue does not become a required gap for the current checkout
- **AND** the current checkout lifecycle remains the source of blocking OpenSpec lifecycle gaps

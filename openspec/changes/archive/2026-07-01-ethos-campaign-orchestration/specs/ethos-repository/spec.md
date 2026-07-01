## ADDED Requirements

### Requirement: Campaign Orchestration

ETHOS SHALL model long-running productization work as campaigns that coordinate
multiple OpenSpec-backed Work Lanes and their closeout state.

#### Scenario: Campaign status reports lane steps

- **GIVEN** `evolution/campaigns/<campaign-id>/campaign.toml` exists
- **WHEN** `ethos campaign status --json` runs
- **THEN** the result includes campaign id, objective, owner, claim id, step
  summary, and ordered steps
- **AND** each step names an OpenSpec change, Work Lane branch, claim id, and
  closeout state.

#### Scenario: Campaign closeout includes campaign package

- **WHEN** `ethos campaign closeout --json` runs
- **THEN** the result includes a campaign closeout package beside local
  closeout, trust closeout, release, parity, shadow parity, and publication
  packages
- **AND** planned future steps do not block closeout before their Work Lane is
  active.

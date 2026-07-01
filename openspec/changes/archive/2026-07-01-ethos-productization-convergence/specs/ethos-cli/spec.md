## MODIFIED Requirements

### Requirement: Public Command Plane
ETHOS SHALL keep the normal user workflow under five transition commands:
`ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`.

#### Scenario: Command surface is classified
- **WHEN** `ethos quality command-registry --json` runs
- **THEN** it reports five public workflow commands
- **AND** it reports `ethos report` as a scorecard command
- **AND** maintainer/reference commands are not counted as advanced public
  workflow commands

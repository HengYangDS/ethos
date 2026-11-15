## MODIFIED Requirements

### Requirement: Adoption continuation preserves request meaning

The shared adoption operation SHALL select one root-bound continuation from the actual request,
binding plan and outcome; after an apply that wrote the release's pin, that continuation SHALL be
`mise lock`, which the caller runs in the adopted root. Preview SHALL require review before
mutation; conflicts and stale input SHALL NOT appear as applied readiness. The planner SHALL NOT own
a competing public next action.

#### Scenario: Preview or blocked adoption is consumed by another client

- **WHEN** a client receives a preview, conflict or denied adoption result
- **THEN** the result preserves its review or recovery requirement and exact root
- **AND** it does not direct the client to status as though adoption had succeeded

#### Scenario: Adoption succeeds outside the target working directory

- **WHEN** an authorized exact adoption applies successfully
- **THEN** the next observation explicitly selects the adopted repository
- **AND** the caller working directory does not change that selection

#### Scenario: An applied adoption wrote the release's pin

- **WHEN** an authorized exact adoption applies and writes the Mise configuration
- **THEN** the next action is exactly `mise lock`
- **AND** an applied adoption that kept the Mise configuration continues with status

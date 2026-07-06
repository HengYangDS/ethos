## ADDED Requirements

### Requirement: Orientation reader view

ETHOS SHALL expose a repository orientation reader view for humans and agents
that derives from repository truth instead of creating a new truth store.

#### Scenario: Orientation reports current capability and boundary

- **WHEN** a user or agent runs `ethos orient --json`
- **THEN** the payload includes `data.orientation.kind = "orientation"`
- **AND** the payload includes `data.orientation.truth_boundary = "repository-reader-view"`
- **AND** the payload includes `data.orientation.mints_truth = false`
- **AND** the payload reports current role, branch, dirtiness, actor capability,
  readiness counts, coordination state, and next actions.

#### Scenario: Status keeps workspace truth pure

- **WHEN** a user or agent runs `ethos status --json`
- **THEN** the existing workspace-status fields remain present
- **AND** no orientation projection is embedded into `data`
- **AND** the orientation view is available through `ethos orient --json` without replacing `status`, `report`, proof, claims, or evidence.

#### Scenario: Foreign lanes are discoverable as observe-only

- **WHEN** another linked Work Lane is visible to the current checkout
- **THEN** orientation includes that lane under coordination
- **AND** the current actor capability for that lane is `observe`
- **AND** write, land, and retire actions remain forbidden unless owner, handoff,
  or maintainer break-glass evidence admits them.

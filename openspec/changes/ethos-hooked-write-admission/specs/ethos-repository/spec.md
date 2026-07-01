## MODIFIED Requirements

### Requirement: Context-bound mutation admission

ETHOS SHALL bind tracked mutation admission to explicit repository root,
checkout role, editor root, target paths, and hook layer before a write-capable
tool can mutate tracked files.

#### Scenario: Implicit-root mutation is blocked

- **WHEN** a write-capable tool does not carry an explicit target root matching
  the current Work Lane
- **THEN** ETHOS blocks the tracked write before filesystem mutation
- **AND** reports the expected root, actual root, checkout role, hook layer,
  and target paths.

#### Scenario: Manual prewrite is degraded mode

- **WHEN** a host cannot install or call the hook admission runtime
- **THEN** the agent MUST run `ethos lane prewrite <paths> --editor-root <root>
  --require-editor-root --json` before tracked writes
- **AND** the terminal design still treats manual prewrite as weaker than a
  bound mutation hook.

### Requirement: Campaign Orchestration

ETHOS SHALL model long-running productization work as campaigns that coordinate
multiple OpenSpec-backed Work Lanes and their closeout state. A campaign is not
a Work Lane; it is a strict serial graph over lane closeouts.

#### Scenario: Campaign step closes before the next active lane

- **WHEN** a campaign step has landed, accepted-root closeout-applied, and its
  Work Lane is retired
- **THEN** the next Work Lane updates the campaign manifest to mark that prior
  step closed
- **AND** activates only its own OpenSpec-backed step before mutation.

#### Scenario: Campaign status exposes lane topology

- **WHEN** `ethos campaign status --json` reports a campaign manifest
- **THEN** each step includes `ordinal`, `depends_on`, `openspec_change`,
  `work_lane`, `claim_id`, and `closeout`
- **AND** the campaign includes `lane_topology.mode = "strict_serial"`
- **AND** dependency edges require upstream closeout retirement before
  downstream activation.
